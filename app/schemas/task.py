import enum
import math
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.db.models import TaskStatus


def _validate_title(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError("title must not be empty or only whitespace")
    return stripped


class TaskSortField(str, enum.Enum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    DUE_DATE = "due_date"
    TITLE = "title"
    STATUS = "status"


class SortOrder(str, enum.Enum):
    ASC = "asc"
    DESC = "desc"


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
    def validate_title(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("title cannot be null")
        return _validate_title(value)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: TaskStatus | None) -> TaskStatus:
        if value is None:
            raise ValueError("status cannot be null")
        return value


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    due_date: date | None
    created_at: datetime
    updated_at: datetime


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool

    @classmethod
    def build(cls, *, page: int, limit: int, total: int) -> "PaginationMeta":
        total_pages = math.ceil(total / limit) if total > 0 else 0
        return cls(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1 and total > 0,
        )


class TaskListResponse(BaseModel):
    data: list[TaskRead]
    pagination: PaginationMeta
