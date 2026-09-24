from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import TaskStatus


def _validate_title(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("title must not be empty or only whitespace")
    return stripped


class TaskCreate(BaseModel):
    title: str = Field(max_length=255)
    description: str | None = None
    status: TaskStatus = TaskStatus.TODO
    due_date: date

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        return _validate_title(value)


class TaskUpdate(BaseModel):
    """All fields optional so a task can be partially updated."""

    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    status: TaskStatus | None = None
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return _validate_title(value)


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    due_date: date | None
    created_at: datetime
    updated_at: datetime
