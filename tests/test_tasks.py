from fastapi.testclient import TestClient


def create_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Write tests",
        "description": "Cover all CRUD endpoints",
        "due_date": "2026-10-15",
    }
    payload.update(overrides)
    return payload


def test_create_task_returns_201(client: TestClient) -> None:
    response = client.post("/api/v1/tasks", json=create_payload())

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], int)
    assert body["id"] > 0
    assert body["title"] == "Write tests"
    assert body["description"] == "Cover all CRUD endpoints"
    assert body["status"] == "todo"
    assert body["due_date"] == "2026-10-15"
    assert "created_at" in body
    assert "updated_at" in body


def test_create_task_defaults_status_to_todo(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks",
        json=create_payload(title="Default status", description=None),
    )

    assert response.status_code == 201
    assert response.json()["status"] == "todo"


def test_create_task_rejects_empty_title(client: TestClient) -> None:
    response = client.post("/api/v1/tasks", json=create_payload(title="   "))

    assert response.status_code == 422
    assert "title must not be empty or only whitespace" in response.text


def test_create_task_rejects_missing_due_date(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks",
        json={"title": "Missing due date", "description": "No date"},
    )

    assert response.status_code == 422


def test_create_task_rejects_invalid_status(client: TestClient) -> None:
    response = client.post(
        "/api/v1/tasks",
        json=create_payload(status="blocked"),
    )

    assert response.status_code == 422


def test_list_tasks_returns_all(client: TestClient) -> None:
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


def test_list_tasks_rejects_invalid_status_filter(client: TestClient) -> None:
    response = client.get("/api/v1/tasks", params={"status": "invalid"})

    assert response.status_code == 422


def test_list_tasks_returns_empty_list(client: TestClient) -> None:
    response = client.get("/api/v1/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_get_task_returns_single_task(client: TestClient) -> None:
    created = client.post("/api/v1/tasks", json=create_payload(title="Fetch me")).json()

    response = client.get(f"/api/v1/tasks/{created['id']}")

    assert response.status_code == 200
    assert response.json()["title"] == "Fetch me"


def test_get_task_returns_404_when_missing(client: TestClient) -> None:
    response = client.get("/api/v1/tasks/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task with id 999 not found"


def test_update_task_partially(client: TestClient) -> None:
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


def test_update_task_rejects_whitespace_title(client: TestClient) -> None:
    created = client.post("/api/v1/tasks", json=create_payload(title="Before")).json()

    response = client.patch(
        f"/api/v1/tasks/{created['id']}",
        json={"title": "   "},
    )

    assert response.status_code == 422
    assert "title must not be empty or only whitespace" in response.text


def test_update_task_returns_404_when_missing(client: TestClient) -> None:
    response = client.patch("/api/v1/tasks/999", json={"title": "Nope"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Task with id 999 not found"


def test_delete_task_returns_204(client: TestClient) -> None:
    created = client.post("/api/v1/tasks", json=create_payload(title="Delete me")).json()

    response = client.delete(f"/api/v1/tasks/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get(f"/api/v1/tasks/{created['id']}").status_code == 404


def test_delete_task_returns_404_when_missing(client: TestClient) -> None:
    response = client.delete("/api/v1/tasks/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Task with id 999 not found"
