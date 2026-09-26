from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.db.models import Task, TaskStatus
from app.schemas.task import (
    PaginationMeta,
    SortOrder,
    TaskCreate,
    TaskSortField,
    TaskUpdate,
)

# Explicit whitelist: API sort field names map to fixed SQLAlchemy columns.
SORT_COLUMN_MAP: dict[TaskSortField, ColumnElement[object]] = {
    TaskSortField.CREATED_AT: Task.created_at,
    TaskSortField.UPDATED_AT: Task.updated_at,
    TaskSortField.DUE_DATE: Task.due_date,
    TaskSortField.TITLE: Task.title,
    TaskSortField.STATUS: Task.status,
}


def create_task(db: Session, payload: TaskCreate, *, user_id: int) -> Task:
    task = Task(
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        due_date=payload.due_date,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(
    db: Session,
    *,
    user_id: int,
    status: TaskStatus | None = None,
    page: int = 1,
    limit: int = 10,
    sort_by: TaskSortField = TaskSortField.CREATED_AT,
    sort_order: SortOrder = SortOrder.DESC,
) -> tuple[list[Task], PaginationMeta]:
    filters: list[ColumnElement[bool]] = [Task.user_id == user_id]
    if status is not None:
        filters.append(Task.status == status)

    count_stmt = select(func.count()).select_from(Task).where(*filters)
    total = db.scalar(count_stmt) or 0

    sort_column = SORT_COLUMN_MAP[sort_by]
    ordering = sort_column.asc() if sort_order == SortOrder.ASC else sort_column.desc()

    stmt = (
        select(Task)
        .where(*filters)
        .order_by(ordering, Task.id)
        .offset((page - 1) * limit)
        .limit(limit)
    )
    tasks = list(db.scalars(stmt).all())

    pagination = PaginationMeta.build(page=page, limit=limit, total=total)
    return tasks, pagination


def get_task(db: Session, task_id: int, *, user_id: int) -> Task | None:
    return db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user_id))


def update_task(db: Session, task: Task, payload: TaskUpdate) -> Task:
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task: Task) -> None:
    db.delete(task)
    db.commit()
