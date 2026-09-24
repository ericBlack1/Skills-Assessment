import os
import subprocess
import time
from collections.abc import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base, get_db
from app.db.models import Task
from app.main import app

TEST_CONTAINER_NAME = "taskmanager-test-pg"
TEST_DB_PORT = 55433


def _normalize_database_url(url: str) -> str:
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return f"postgresql+psycopg://{url[len(prefix):]}"
    return url


def _wait_for_postgres(database_url: str, timeout_seconds: int = 30) -> None:
    engine = create_engine(database_url, pool_pre_ping=True)
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with engine.connect() as connection:
                connection.exec_driver_sql("SELECT 1")
            engine.dispose()
            return
        except Exception as exc:  # noqa: BLE001 - retry until timeout
            last_error = exc
            time.sleep(1)
    engine.dispose()
    raise RuntimeError("Test PostgreSQL did not become ready in time") from last_error


def _start_docker_test_database() -> str:
    subprocess.run(
        ["docker", "rm", "-f", TEST_CONTAINER_NAME],
        check=False,
        capture_output=True,
    )
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            TEST_CONTAINER_NAME,
            "-e",
            "POSTGRES_USER=taskmanager_test",
            "-e",
            "POSTGRES_PASSWORD=testpassword",
            "-e",
            "POSTGRES_DB=taskmanager_test",
            "-p",
            f"{TEST_DB_PORT}:5432",
            "postgres:16-alpine",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    database_url = (
        "postgresql+psycopg://taskmanager_test:testpassword"
        f"@localhost:{TEST_DB_PORT}/taskmanager_test"
    )
    _wait_for_postgres(database_url)
    return database_url


def _resolve_test_database_url() -> tuple[str, bool]:
    """Return the test database URL and whether this session started Docker."""
    configured_url = os.getenv("TEST_DATABASE_URL")
    production_url = os.getenv("DATABASE_URL")

    if configured_url:
        test_url = _normalize_database_url(configured_url)
        if production_url and _normalize_database_url(production_url) == test_url:
            raise RuntimeError(
                "TEST_DATABASE_URL must not be the same as DATABASE_URL. "
                "Use a dedicated test database to avoid modifying production data."
            )
        return test_url, False

    return _start_docker_test_database(), True


@pytest.fixture(scope="session")
def test_database_url() -> Generator[str, None, None]:
    url, started_docker = _resolve_test_database_url()
    yield url
    if started_docker:
        subprocess.run(
            ["docker", "rm", "-f", TEST_CONTAINER_NAME],
            check=False,
            capture_output=True,
        )


@pytest.fixture(scope="session")
def test_engine(test_database_url: str) -> Generator[Engine, None, None]:
    engine = create_engine(test_database_url, pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """Provide an isolated SQLAlchemy session that rolls back after each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def assert_clean_task_table(db_session: Session) -> None:
    """Ensure each test starts with an empty tasks table."""
    assert db_session.scalars(select(Task)).all() == []
