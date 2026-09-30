from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Task, User
from tests.conftest import AuthenticatedClient


def create_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Shared title",
        "description": "Isolation test task",
        "due_date": "2026-10-15",
    }
    payload.update(overrides)
    return payload


def test_create_task_assigns_authenticated_user(
    auth_client: AuthenticatedClient,
    db_session: Session,
) -> None:
    response = auth_client.post("/api/v1/tasks", json=create_payload(title="Owned"))

    assert response.status_code == 201
    task_id = response.json()["id"]

    stored = db_session.get(Task, task_id)
    owner = db_session.scalar(
        select(User).where(User.email == "testuser@example.com")
    )
    assert stored is not None
    assert owner is not None
    assert stored.user_id == owner.id


def test_user_cannot_get_another_users_task(
    auth_client: AuthenticatedClient,
    other_auth_client: AuthenticatedClient,
) -> None:
    created = auth_client.post("/api/v1/tasks", json=create_payload(title="Private")).json()

    response = other_auth_client.get(f"/api/v1/tasks/{created['id']}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_user_cannot_update_another_users_task(
    auth_client: AuthenticatedClient,
    other_auth_client: AuthenticatedClient,
) -> None:
    created = auth_client.post("/api/v1/tasks", json=create_payload(title="Before")).json()

    response = other_auth_client.patch(
        f"/api/v1/tasks/{created['id']}",
        json={"title": "Hijacked"},
    )

    assert response.status_code == 404
    assert auth_client.get(f"/api/v1/tasks/{created['id']}").json()["title"] == "Before"


def test_user_cannot_delete_another_users_task(
    auth_client: AuthenticatedClient,
    other_auth_client: AuthenticatedClient,
) -> None:
    created = auth_client.post("/api/v1/tasks", json=create_payload(title="Keep me")).json()

    response = other_auth_client.delete(f"/api/v1/tasks/{created['id']}")

    assert response.status_code == 404
    assert auth_client.get(f"/api/v1/tasks/{created['id']}").status_code == 200


def test_list_returns_only_current_users_tasks(
    auth_client: AuthenticatedClient,
    other_auth_client: AuthenticatedClient,
) -> None:
    auth_client.post("/api/v1/tasks", json=create_payload(title="User A task 1"))
    auth_client.post("/api/v1/tasks", json=create_payload(title="User A task 2"))
    other_auth_client.post("/api/v1/tasks", json=create_payload(title="User B task"))

    response = auth_client.get("/api/v1/tasks", params={"limit": 100})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 2
    assert body["pagination"]["total"] == 2
    assert {task["title"] for task in body["data"]} == {"User A task 1", "User A task 2"}


def test_other_user_list_excludes_first_users_tasks(
    auth_client: AuthenticatedClient,
    other_auth_client: AuthenticatedClient,
) -> None:
    auth_client.post("/api/v1/tasks", json=create_payload(title="User A only"))
    other_auth_client.post("/api/v1/tasks", json=create_payload(title="User B only"))

    response = other_auth_client.get("/api/v1/tasks", params={"limit": 100})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["title"] == "User B only"
    assert body["pagination"]["total"] == 1


def test_pagination_and_filtering_stay_scoped_to_user(
    auth_client: AuthenticatedClient,
    other_auth_client: AuthenticatedClient,
) -> None:
    auth_client.post(
        "/api/v1/tasks",
        json=create_payload(title="A todo", status="todo"),
    )
    auth_client.post(
        "/api/v1/tasks",
        json=create_payload(title="A done", status="done"),
    )
    other_auth_client.post(
        "/api/v1/tasks",
        json=create_payload(title="B todo", status="todo"),
    )

    response = auth_client.get("/api/v1/tasks", params={"status": "todo"})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["title"] == "A todo"
    assert body["pagination"]["total"] == 1


def test_sorting_stays_scoped_to_user(
    auth_client: AuthenticatedClient,
    other_auth_client: AuthenticatedClient,
) -> None:
    auth_client.post(
        "/api/v1/tasks",
        json=create_payload(title="Alpha", due_date="2026-10-01"),
    )
    auth_client.post(
        "/api/v1/tasks",
        json=create_payload(title="Bravo", due_date="2026-10-02"),
    )
    other_auth_client.post(
        "/api/v1/tasks",
        json=create_payload(title="Charlie", due_date="2026-10-03"),
    )

    response = auth_client.get(
        "/api/v1/tasks",
        params={"sort_by": "title", "sort_order": "asc", "limit": 100},
    )

    assert response.status_code == 200
    titles = [task["title"] for task in response.json()["data"]]
    assert titles == ["Alpha", "Bravo"]


def test_cross_user_access_returns_404_not_403(
    auth_client: AuthenticatedClient,
    other_auth_client: AuthenticatedClient,
) -> None:
    """Other users' tasks should not leak existence via 403."""
    created = auth_client.post("/api/v1/tasks", json=create_payload(title="Hidden")).json()

    for method, url, body in [
        ("get", f"/api/v1/tasks/{created['id']}", None),
        ("patch", f"/api/v1/tasks/{created['id']}", {"title": "Nope"}),
        ("delete", f"/api/v1/tasks/{created['id']}", None),
    ]:
        if method == "get":
            response = other_auth_client.get(url)
        elif method == "patch":
            response = other_auth_client.patch(url, json=body)
        else:
            response = other_auth_client.delete(url)

        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TASK_NOT_FOUND"
