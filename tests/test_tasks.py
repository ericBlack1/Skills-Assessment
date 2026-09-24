from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models import Task


def create_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Write tests",
        "description": "Cover all CRUD endpoints",
        "due_date": "2026-10-15",
    }
    payload.update(overrides)
    return payload


def test_create_task_success(client: TestClient, db_session: Session) -> None:
    response = client.post("/api/v1/tasks", json=create_payload())

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


def test_list_tasks_returns_all_tasks(client: TestClient) -> None:
    client.post("/api/v1/tasks", json=create_payload(title="First"))
    client.post(
        "/api/v1/tasks",
        json=create_payload(title="Second", status="in-progress"),
    )

    response = client.get("/api/v1/tasks")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert [task["title"] for task in body] == ["First", "Second"]


def test_get_task_returns_single_task(client: TestClient) -> None:
    created = client.post("/api/v1/tasks", json=create_payload(title="Fetch me")).json()

    response = client.get(f"/api/v1/tasks/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["title"] == "Fetch me"
    assert body["status"] == "todo"


def test_update_task_changes_fields(client: TestClient, db_session: Session) -> None:
    created = client.post("/api/v1/tasks", json=create_payload(title="Before")).json()

    response = client.patch(
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


def test_delete_task_removes_record(client: TestClient, db_session: Session) -> None:
    created = client.post("/api/v1/tasks", json=create_payload(title="Delete me")).json()

    response = client.delete(f"/api/v1/tasks/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert db_session.get(Task, created["id"]) is None
    assert client.get(f"/api/v1/tasks/{created['id']}").status_code == 404


def test_list_tasks_filters_by_status(client: TestClient) -> None:
    client.post("/api/v1/tasks", json=create_payload(title="Todo task"))
    client.post(
        "/api/v1/tasks",
        json=create_payload(title="Active task", status="in-progress"),
    )
    client.post(
        "/api/v1/tasks",
        json=create_payload(title="Done task", status="done"),
    )

    response = client.get("/api/v1/tasks", params={"status": "in-progress"})

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Active task"
    assert body[0]["status"] == "in-progress"


def test_list_tasks_returns_empty_list_when_no_matches(client: TestClient) -> None:
    response = client.get("/api/v1/tasks", params={"status": "done"})

    assert response.status_code == 200
    assert response.json() == []


def test_create_task_rejects_missing_title(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks",
        json={"description": "No title", "due_date": "2026-10-15"},
    )

    assert response.status_code == 422


def test_create_task_rejects_empty_title(client: TestClient) -> None:
    response = client.post("/api/v1/tasks", json=create_payload(title="   "))

    assert response.status_code == 422
    assert "title must not be empty or only whitespace" in response.text


def test_create_task_rejects_invalid_status(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks",
        json=create_payload(status="blocked"),
    )

    assert response.status_code == 422


def test_list_tasks_rejects_invalid_status_filter(client: TestClient) -> None:
    response = client.get("/api/v1/tasks", params={"status": "invalid"})

    assert response.status_code == 422


def test_get_task_returns_404_for_missing_task(client: TestClient) -> None:
    response = client.get("/api/v1/tasks/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task with id 999999 not found"


def test_update_task_returns_404_for_missing_task(client: TestClient) -> None:
    response = client.patch("/api/v1/tasks/999999", json={"title": "Nope"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Task with id 999999 not found"


def test_delete_task_returns_404_for_missing_task(client: TestClient) -> None:
    response = client.delete("/api/v1/tasks/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task with id 999999 not found"


def test_create_task_rejects_missing_due_date(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks",
        json={"title": "Missing due date", "description": "No date"},
    )

    assert response.status_code == 422


def test_create_task_rejects_invalid_due_date(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks",
        json=create_payload(due_date="not-a-date"),
    )

    assert response.status_code == 422


def test_update_task_rejects_whitespace_title(client: TestClient) -> None:
    created = client.post("/api/v1/tasks", json=create_payload(title="Before")).json()

    response = client.patch(
        f"/api/v1/tasks/{created['id']}",
        json={"title": "   "},
    )

    assert response.status_code == 422
    assert "title must not be empty or only whitespace" in response.text
