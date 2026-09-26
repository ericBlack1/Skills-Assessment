from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Task, User
from tests.conftest import AuthenticatedClient


def create_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Write tests",
        "description": "Cover all CRUD endpoints",
        "due_date": "2026-10-15",
    }
    payload.update(overrides)
    return payload


def test_create_task_success(auth_client: AuthenticatedClient, db_session: Session) -> None:
    response = auth_client.post("/api/v1/tasks", json=create_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Write tests"
    assert body["description"] == "Cover all CRUD endpoints"
    assert body["status"] == "todo"
    assert body["due_date"] == "2026-10-15"
    assert isinstance(body["id"], int)
    assert body["id"] > 0
    assert "created_at" in body
    assert "updated_at" in body

    stored = db_session.get(Task, body["id"])
    assert stored is not None
    assert stored.title == "Write tests"
    assert stored.status.value == "todo"
    owner = db_session.scalar(
        select(User).where(User.email == "testuser@example.com")
    )
    assert owner is not None
    assert stored.user_id == owner.id


def test_list_tasks_returns_all_tasks(auth_client: AuthenticatedClient) -> None:
    auth_client.post("/api/v1/tasks", json=create_payload(title="First"))
    auth_client.post(
        "/api/v1/tasks",
        json=create_payload(title="Second", status="in-progress"),
    )

    response = auth_client.get("/api/v1/tasks", params={"limit": 100})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert {task["title"] for task in body["data"]} == {"First", "Second"}
    assert body["pagination"]["total"] == 2


def test_get_task_returns_single_task(auth_client: AuthenticatedClient) -> None:
    created = auth_client.post("/api/v1/tasks", json=create_payload(title="Fetch me")).json()

    response = auth_client.get(f"/api/v1/tasks/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["title"] == "Fetch me"
    assert body["status"] == "todo"


def test_update_task_changes_fields(auth_client: AuthenticatedClient, db_session: Session) -> None:
    created = auth_client.post("/api/v1/tasks", json=create_payload(title="Before")).json()

    response = auth_client.patch(
        f"/api/v1/tasks/{created['id']}",
        json={"title": "After", "status": "done"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "After"
    assert body["status"] == "done"
    assert body["due_date"] == "2026-10-15"

    stored = db_session.get(Task, created["id"])
    assert stored is not None
    assert stored.title == "After"
    assert stored.status.value == "done"


def test_delete_task_removes_record(auth_client: AuthenticatedClient, db_session: Session) -> None:
    created = auth_client.post("/api/v1/tasks", json=create_payload(title="Delete me")).json()

    response = auth_client.delete(f"/api/v1/tasks/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert db_session.get(Task, created["id"]) is None
    assert auth_client.get(f"/api/v1/tasks/{created['id']}").status_code == 404


def test_list_tasks_filters_by_status(auth_client: AuthenticatedClient) -> None:
    auth_client.post("/api/v1/tasks", json=create_payload(title="Todo task"))
    auth_client.post(
        "/api/v1/tasks",
        json=create_payload(title="Active task", status="in-progress"),
    )
    auth_client.post(
        "/api/v1/tasks",
        json=create_payload(title="Done task", status="done"),
    )

    response = auth_client.get("/api/v1/tasks", params={"status": "in-progress"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["title"] == "Active task"
    assert body["data"][0]["status"] == "in-progress"
    assert body["pagination"]["total"] == 1


def test_list_tasks_returns_empty_list_when_no_matches(auth_client: AuthenticatedClient) -> None:
    response = auth_client.get("/api/v1/tasks", params={"status": "done"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["pagination"]["total"] == 0


def test_create_task_rejects_missing_title(auth_client: AuthenticatedClient) -> None:
    response = auth_client.post(
        "/api/v1/tasks",
        json={"description": "No title", "due_date": "2026-10-15"},
    )

    assert response.status_code == 422


def test_create_task_rejects_empty_title(auth_client: AuthenticatedClient) -> None:
    response = auth_client.post("/api/v1/tasks", json=create_payload(title="   "))

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(
        "title must not be empty or only whitespace" in item["message"]
        for item in body["error"]["details"]
    )


def test_create_task_rejects_invalid_status(auth_client: AuthenticatedClient) -> None:
    response = auth_client.post(
        "/api/v1/tasks",
        json=create_payload(status="blocked"),
    )

    assert response.status_code == 422


def test_list_tasks_rejects_invalid_status_filter(auth_client: AuthenticatedClient) -> None:
    response = auth_client.get("/api/v1/tasks", params={"status": "invalid"})

    assert response.status_code == 422


def test_get_task_returns_404_for_missing_task(auth_client: AuthenticatedClient) -> None:
    response = auth_client.get("/api/v1/tasks/999999")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "TASK_NOT_FOUND"
    assert body["message"] == "Task not found"


def test_update_task_returns_404_for_missing_task(auth_client: AuthenticatedClient) -> None:
    response = auth_client.patch("/api/v1/tasks/999999", json={"title": "Nope"})

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "TASK_NOT_FOUND"


def test_delete_task_returns_404_for_missing_task(auth_client: AuthenticatedClient) -> None:
    response = auth_client.delete("/api/v1/tasks/999999")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "TASK_NOT_FOUND"


def test_create_task_rejects_missing_due_date(auth_client: AuthenticatedClient) -> None:
    response = auth_client.post(
        "/api/v1/tasks",
        json={"title": "Missing due date", "description": "No date"},
    )

    assert response.status_code == 422


def test_create_task_rejects_invalid_due_date(auth_client: AuthenticatedClient) -> None:
    response = auth_client.post(
        "/api/v1/tasks",
        json=create_payload(due_date="not-a-date"),
    )

    assert response.status_code == 422


def test_update_task_rejects_whitespace_title(auth_client: AuthenticatedClient) -> None:
    created = auth_client.post("/api/v1/tasks", json=create_payload(title="Before")).json()

    response = auth_client.patch(
        f"/api/v1/tasks/{created['id']}",
        json={"title": "   "},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(
        "title must not be empty or only whitespace" in item["message"]
        for item in body["error"]["details"]
    )
