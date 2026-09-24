from fastapi.testclient import TestClient


def create_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Write tests",
        "description": "Cover pagination",
        "due_date": "2026-10-15",
    }
    payload.update(overrides)
    return payload


def seed_tasks(client: TestClient, count: int, **overrides: object) -> None:
    for index in range(count):
        client.post(
            "/api/v1/tasks",
            json=create_payload(
                title=f"Task {index:02d}",
                due_date=f"2026-10-{(index % 28) + 1:02d}",
                **overrides,
            ),
        )


def test_list_tasks_default_pagination(client: TestClient) -> None:
    seed_tasks(client, 12)

    response = client.get("/api/v1/tasks")

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 10
    assert body["pagination"] == {
        "page": 1,
        "limit": 10,
        "total": 12,
        "total_pages": 2,
        "has_next": True,
        "has_previous": False,
    }


def test_list_tasks_custom_page_and_limit(client: TestClient) -> None:
    seed_tasks(client, 25)

    response = client.get("/api/v1/tasks", params={"page": 2, "limit": 20})

    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 5
    assert body["pagination"]["page"] == 2
    assert body["pagination"]["limit"] == 20
    assert body["pagination"]["total"] == 25
    assert body["pagination"]["total_pages"] == 2
    assert body["pagination"]["has_next"] is False
    assert body["pagination"]["has_previous"] is True


def test_list_tasks_rejects_limit_above_maximum(client: TestClient) -> None:
    response = client.get("/api/v1/tasks", params={"limit": 101})

    assert response.status_code == 422


def test_list_tasks_rejects_page_below_one(client: TestClient) -> None:
    response = client.get("/api/v1/tasks", params={"page": 0})

    assert response.status_code == 422


def test_list_tasks_sorts_ascending_by_title(client: TestClient) -> None:
    client.post("/api/v1/tasks", json=create_payload(title="Charlie", due_date="2026-10-03"))
    client.post("/api/v1/tasks", json=create_payload(title="Alpha", due_date="2026-10-01"))
    client.post("/api/v1/tasks", json=create_payload(title="Bravo", due_date="2026-10-02"))

    response = client.get(
        "/api/v1/tasks",
        params={"sort_by": "title", "sort_order": "asc", "limit": 100},
    )

    assert response.status_code == 200
    titles = [task["title"] for task in response.json()["data"]]
    assert titles == ["Alpha", "Bravo", "Charlie"]


def test_list_tasks_sorts_descending_by_due_date(client: TestClient) -> None:
    client.post("/api/v1/tasks", json=create_payload(title="Early", due_date="2026-10-01"))
    client.post("/api/v1/tasks", json=create_payload(title="Late", due_date="2026-10-31"))
    client.post("/api/v1/tasks", json=create_payload(title="Mid", due_date="2026-10-15"))

    response = client.get(
        "/api/v1/tasks",
        params={"sort_by": "due_date", "sort_order": "desc", "limit": 100},
    )

    assert response.status_code == 200
    titles = [task["title"] for task in response.json()["data"]]
    assert titles == ["Late", "Mid", "Early"]


def test_list_tasks_rejects_invalid_sort_field(client: TestClient) -> None:
    response = client.get("/api/v1/tasks", params={"sort_by": "id"})

    assert response.status_code == 422


def test_list_tasks_rejects_invalid_sort_order(client: TestClient) -> None:
    response = client.get("/api/v1/tasks", params={"sort_order": "sideways"})

    assert response.status_code == 422


def test_list_tasks_pagination_with_status_filter(client: TestClient) -> None:
    for index in range(5):
        client.post(
            "/api/v1/tasks",
            json=create_payload(title=f"Todo {index:02d}", status="todo"),
        )
    for index in range(3):
        client.post(
            "/api/v1/tasks",
            json=create_payload(title=f"Active {index:02d}", status="in-progress"),
        )

    response = client.get(
        "/api/v1/tasks",
        params={"status": "todo", "page": 2, "limit": 2, "sort_by": "title", "sort_order": "asc"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"]["total"] == 5
    assert body["pagination"]["total_pages"] == 3
    assert len(body["data"]) == 2
    assert all(task["status"] == "todo" for task in body["data"])
    assert body["data"][0]["title"] == "Todo 02"


def test_list_tasks_returns_empty_page_with_metadata(client: TestClient) -> None:
    seed_tasks(client, 3)

    response = client.get("/api/v1/tasks", params={"page": 5, "limit": 10})

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["pagination"] == {
        "page": 5,
        "limit": 10,
        "total": 3,
        "total_pages": 1,
        "has_next": False,
        "has_previous": True,
    }


def test_list_tasks_returns_empty_result_with_zero_total(client: TestClient) -> None:
    response = client.get("/api/v1/tasks", params={"status": "done"})

    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["pagination"]["total"] == 0
    assert body["pagination"]["total_pages"] == 0
    assert body["pagination"]["has_next"] is False
    assert body["pagination"]["has_previous"] is False
