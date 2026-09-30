from sqlalchemy.exc import SQLAlchemyError

from app.services import task_service
from tests.conftest import AuthenticatedClient


def create_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Write tests",
        "description": "Cover error handling",
        "due_date": "2026-10-15",
    }
    payload.update(overrides)
    return payload


def assert_error_shape(body: dict[str, object], *, status_code: int, code: str) -> None:
    assert body["success"] is False
    assert body["statusCode"] == status_code
    assert body["data"] is None
    assert body["error"]["code"] == code
    assert "message" in body


def test_missing_title_returns_422_with_field_details(auth_client: AuthenticatedClient) -> None:
    response = auth_client.post(
        "/api/v1/tasks",
        json={"description": "No title", "due_date": "2026-10-15"},
    )

    assert response.status_code == 422
    body = response.json()
    assert_error_shape(body, status_code=422, code="VALIDATION_ERROR")
    assert body["message"] == "Validation failed"
    fields = {item["field"] for item in body["error"]["details"]}
    assert "title" in fields


def test_invalid_status_returns_422_with_field_details(auth_client: AuthenticatedClient) -> None:
    response = auth_client.post(
        "/api/v1/tasks",
        json=create_payload(status="blocked"),
    )

    assert response.status_code == 422
    body = response.json()
    assert_error_shape(body, status_code=422, code="VALIDATION_ERROR")
    fields = {item["field"] for item in body["error"]["details"]}
    assert "status" in fields


def test_invalid_pagination_returns_422(auth_client: AuthenticatedClient) -> None:
    response = auth_client.get("/api/v1/tasks", params={"page": 0, "limit": 101})

    assert response.status_code == 422
    body = response.json()
    assert_error_shape(body, status_code=422, code="VALIDATION_ERROR")
    fields = {item["field"] for item in body["error"]["details"]}
    assert "page" in fields
    assert "limit" in fields


def test_invalid_sort_field_returns_422(auth_client: AuthenticatedClient) -> None:
    response = auth_client.get("/api/v1/tasks", params={"sort_by": "id"})

    assert response.status_code == 422
    body = response.json()
    assert_error_shape(body, status_code=422, code="VALIDATION_ERROR")
    assert any(item["field"] == "sort_by" for item in body["error"]["details"])


def test_nonexistent_task_returns_404(auth_client: AuthenticatedClient) -> None:
    response = auth_client.get("/api/v1/tasks/999999")

    assert response.status_code == 404
    body = response.json()
    assert_error_shape(body, status_code=404, code="TASK_NOT_FOUND")
    assert body["message"] == "Task not found"
    assert body["error"]["details"] is None


def test_database_error_returns_safe_500(auth_client: AuthenticatedClient, monkeypatch) -> None:
    class FakeDatabaseError(SQLAlchemyError):
        pass

    def failing_list_tasks(*_args, **_kwargs):
        raise FakeDatabaseError("connection failed")

    monkeypatch.setattr(task_service, "list_tasks", failing_list_tasks)

    response = auth_client.get("/api/v1/tasks")

    assert response.status_code == 500
    body = response.json()
    assert_error_shape(body, status_code=500, code="DATABASE_ERROR")
    assert body["message"] == "A database error occurred"
    assert "connection failed" not in response.text
    assert "Traceback" not in response.text


def test_patch_null_title_returns_422(auth_client: AuthenticatedClient) -> None:
    created = auth_client.post("/api/v1/tasks", json=create_payload(title="Patch target")).json()

    response = auth_client.patch(
        f"/api/v1/tasks/{created['id']}",
        json={"title": None},
    )

    assert response.status_code == 422
    body = response.json()
    assert_error_shape(body, status_code=422, code="VALIDATION_ERROR")
    assert any(item["field"] == "title" for item in body["error"]["details"])
    assert "title cannot be null" in response.text
    assert "DATABASE_ERROR" not in response.text


def test_patch_null_status_returns_422(auth_client: AuthenticatedClient) -> None:
    created = auth_client.post("/api/v1/tasks", json=create_payload(title="Patch target")).json()

    response = auth_client.patch(
        f"/api/v1/tasks/{created['id']}",
        json={"status": None},
    )

    assert response.status_code == 422
    body = response.json()
    assert_error_shape(body, status_code=422, code="VALIDATION_ERROR")
    assert any(item["field"] == "status" for item in body["error"]["details"])
    assert "status cannot be null" in response.text
    assert "DATABASE_ERROR" not in response.text


def test_patch_empty_body_still_works(auth_client: AuthenticatedClient) -> None:
    created = auth_client.post("/api/v1/tasks", json=create_payload(title="Unchanged")).json()

    response = auth_client.patch(f"/api/v1/tasks/{created['id']}", json={})

    assert response.status_code == 200
    assert response.json()["title"] == "Unchanged"


def test_unexpected_error_returns_safe_500(auth_client: AuthenticatedClient, monkeypatch) -> None:
    def failing_get_task(*_args, **_kwargs):
        raise RuntimeError("something broke internally")

    monkeypatch.setattr(task_service, "get_task", failing_get_task)

    response = auth_client.get("/api/v1/tasks/1")

    assert response.status_code == 500
    body = response.json()
    assert_error_shape(body, status_code=500, code="INTERNAL_SERVER_ERROR")
    assert body["message"] == "An unexpected error occurred"
    assert "something broke internally" not in response.text
    assert "Traceback" not in response.text
