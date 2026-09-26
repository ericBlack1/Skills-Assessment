from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import User


def register_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "email": "user@example.com",
        "password": "securepass123",
    }
    payload.update(overrides)
    return payload


def task_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": "Auth test task",
        "due_date": "2026-10-15",
    }
    payload.update(overrides)
    return payload


def test_register_returns_201_and_jwt(client: TestClient, db_session: Session) -> None:
    response = client.post("/api/v1/auth/register", json=register_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Registration successful"
    assert body["metadata"] is None
    assert body["data"]["token_type"] == "Bearer"
    assert body["data"]["expires_in"] == settings.jwt_expire_minutes * 60
    assert isinstance(body["data"]["access_token"], str)
    assert len(body["data"]["access_token"]) > 0

    user = db_session.scalar(select(User).where(User.email == "user@example.com"))
    assert user is not None

    decoded = jwt.decode(
        body["data"]["access_token"],
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    assert decoded["sub"] == str(user.id)


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=register_payload())

    response = client.post("/api/v1/auth/register", json=register_payload())

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "EMAIL_ALREADY_REGISTERED"
    assert body["message"] == "Email already registered"


def test_register_duplicate_email_is_case_insensitive(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=register_payload(email="User@Example.com"))

    response = client.post(
        "/api/v1/auth/register",
        json=register_payload(email="user@example.com"),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_register_rejects_invalid_email(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json=register_payload(email="not-an-email"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_register_rejects_short_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json=register_payload(password="short"),
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any(item["field"] == "password" for item in body["error"]["details"])


def test_register_stores_hashed_password_not_plaintext(
    client: TestClient,
    db_session: Session,
) -> None:
    password = "securepass123"
    client.post("/api/v1/auth/register", json=register_payload(password=password))

    user = db_session.scalar(select(User).where(User.email == "user@example.com"))
    assert user is not None
    assert user.hashed_password != password
    assert user.hashed_password.startswith("$2")


def test_login_returns_jwt(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=register_payload())

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "securepass123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Login successful"
    assert body["metadata"] is None
    assert body["data"]["token_type"] == "Bearer"
    assert body["data"]["expires_in"] == settings.jwt_expire_minutes * 60
    assert isinstance(body["data"]["access_token"], str)


def test_login_accepts_email_case_insensitively(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=register_payload(email="User@Example.com"))

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "USER@EXAMPLE.COM", "password": "securepass123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "access_token" in body["data"]


def test_login_invalid_password_returns_401(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=register_payload())

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert body["message"] == "Invalid email or password"


def test_login_unknown_email_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "securepass123"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_register_token_can_create_task(client: TestClient) -> None:
    register_response = client.post("/api/v1/auth/register", json=register_payload())
    token = register_response.json()["data"]["access_token"]

    response = client.post(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
        json=task_payload(),
    )

    assert response.status_code == 201
    assert response.json()["title"] == "Auth test task"


@pytest.mark.parametrize(
    ("method", "url", "json_body"),
    [
        ("get", "/api/v1/tasks", None),
        ("post", "/api/v1/tasks", {"title": "No auth", "due_date": "2026-10-15"}),
        ("get", "/api/v1/tasks/1", None),
        ("patch", "/api/v1/tasks/1", {"title": "No auth"}),
        ("delete", "/api/v1/tasks/1", None),
    ],
)
def test_task_endpoints_require_authentication(
    client: TestClient,
    method: str,
    url: str,
    json_body: dict[str, object] | None,
) -> None:
    response = client.request(method, url, json=json_body)

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["message"] == "Authentication required"


def test_tasks_reject_invalid_token(client: TestClient) -> None:
    response = client.get(
        "/api/v1/tasks",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_tasks_reject_expired_token(client: TestClient) -> None:
    expired_token = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) - timedelta(minutes=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_tasks_reject_token_signed_with_wrong_secret(client: TestClient) -> None:
    forged_token = jwt.encode(
        {"sub": "1", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        "wrong-secret",
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {forged_token}"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_tasks_reject_token_for_unknown_user(client: TestClient) -> None:
    token = jwt.encode(
        {"sub": "999999", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )

    response = client.get(
        "/api/v1/tasks",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_tasks_reject_malformed_authorization_header(client: TestClient) -> None:
    response = client.get(
        "/api/v1/tasks",
        headers={"Authorization": "Token not-bearer-format"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_tasks_accept_valid_token(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get("/api/v1/tasks", headers=auth_headers)

    assert response.status_code == 200
