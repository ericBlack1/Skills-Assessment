from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db.database import SessionLocal
from app.db.models import Task
from app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_tasks() -> Generator[None, None, None]:
    """Remove all tasks before and after each test."""
    with SessionLocal() as session:
        session.execute(delete(Task))
        session.commit()
    yield
    with SessionLocal() as session:
        session.execute(delete(Task))
        session.commit()
