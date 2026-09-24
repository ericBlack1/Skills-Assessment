from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import TaskStatus
from app.schemas.task import (
    SortOrder,
    TaskCreate,
    TaskListResponse,
    TaskRead,
    TaskSortField,
    TaskUpdate,
)
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])

DbSession = Annotated[Session, Depends(get_db)]


@router.post(
    "",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
    description="Create a new task. Title and due_date are required; status defaults to todo.",
)
def create_task(payload: TaskCreate, db: DbSession) -> TaskRead:
    return task_service.create_task(db, payload)


@router.get(
    "",
    response_model=TaskListResponse,
    summary="List tasks",
    description=(
        "Return a paginated list of tasks. Supports filtering by status, "
        "sorting by whitelisted fields, and page/limit pagination."
    ),
)
def list_tasks(
    db: DbSession,
    status_filter: Annotated[
        TaskStatus | None,
        Query(
            alias="status",
            description="Filter tasks by status: todo, in-progress, or done.",
        ),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (starts at 1).")] = 1,
    limit: Annotated[
        int, Query(ge=1, le=100, description="Number of tasks per page (max 100).")
    ] = 10,
    sort_by: Annotated[
        TaskSortField,
        Query(description="Field to sort by."),
    ] = TaskSortField.CREATED_AT,
    sort_order: Annotated[
        SortOrder,
        Query(description="Sort direction: asc or desc."),
    ] = SortOrder.DESC,
) -> TaskListResponse:
    tasks, pagination = task_service.list_tasks(
        db,
        status=status_filter,
        page=page,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return TaskListResponse(data=tasks, pagination=pagination)


@router.get(
    "/{task_id}",
    response_model=TaskRead,
    summary="Get a task",
    description="Return a single task by ID.",
)
def get_task(task_id: int, db: DbSession) -> TaskRead:
    task = task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )
    return task


@router.patch(
    "/{task_id}",
    response_model=TaskRead,
    summary="Update a task",
    description="Partially update a task. Only supplied fields are changed.",
)
def update_task(task_id: int, payload: TaskUpdate, db: DbSession) -> TaskRead:
    task = task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )
    return task_service.update_task(db, task, payload)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    description="Permanently delete a task by ID.",
)
def delete_task(task_id: int, db: DbSession) -> None:
    task = task_service.get_task(db, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )
    task_service.delete_task(db, task)
