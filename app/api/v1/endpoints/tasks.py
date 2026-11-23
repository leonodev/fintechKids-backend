from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, verify_parent_ownership
from app.core.audit import record_activity
from app.core.errors import AppHTTPException, ErrorCode, api_error_responses
from app.db.session import get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.task import (
    TaskCreate,
    TaskDeleteResponse,
    TaskResponse,
    TaskStatusEnum,
    TaskUpdate,
)

router = APIRouter()


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="1. Create a new family task (by parent)",
    description=(
        "Registers a new family task receiving `name`, `time_granted`, `coins_granted`, "
        "`email_parent`, `description`, and `status` (defaults to `enable` automatically). "
        "The `created_at` field is auto-generated in UTC (JWT Protected)."
    ),
    responses=api_error_responses(
        ErrorCode.INVALID_OR_EXPIRED_TOKEN,
        ErrorCode.PARENT_EMAIL_NOT_FOUND,
        ErrorCode.PARENT_EMAIL_MISMATCH,
    ),
)
def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    parent_user = verify_parent_ownership(db, task_in.email_parent, current_user)

    task = Task(
        name=task_in.name,
        time_granted=task_in.time_granted,
        coins_granted=task_in.coins_granted,
        email_parent=parent_user.email_parent,
        description=task_in.description,
        status=task_in.status.value,
        parent_id=parent_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        action="CREATE_TASK",
        entity_type="tasks",
        entity_id=task.id,
        details=f"Tarea creada: '{task.name}' (status={task.status}, coins_granted={task.coins_granted})",
    )
    return task


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="2. Edit a family task (including enabling/disabling status)",
    description=(
        "Allows the parent to edit any field of a task (`name`, `time_granted`, `coins_granted`, "
        "`description`) as well as toggle its `status` between `enable` and `disable` (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.TASK_NOT_FOUND),
)
def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Task:
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.parent_id == current_user.id)
        .first()
    )
    if not task:
        raise AppHTTPException(error_code=ErrorCode.TASK_NOT_FOUND)

    if task_in.name is not None:
        task.name = task_in.name
    if task_in.time_granted is not None:
        task.time_granted = task_in.time_granted
    if task_in.coins_granted is not None:
        task.coins_granted = task_in.coins_granted
    if task_in.description is not None:
        task.description = task_in.description
    if task_in.status is not None:
        task.status = task_in.status.value

    task.updated_at = datetime.now(timezone.utc)
    db.add(task)
    db.commit()
    db.refresh(task)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        action="UPDATE_TASK",
        entity_type="tasks",
        entity_id=task.id,
        details=f"Tarea actualizada: '{task.name}' (status={task.status}, coins_granted={task.coins_granted})",
    )
    return task


@router.get(
    "",
    response_model=List[TaskResponse],
    summary="3. List all family tasks (any status)",
    description=(
        "Returns all tasks belonging exclusively to the authenticated parent's family "
        "regardless of their status (`enable` and `disable`) (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.PARENT_EMAIL_MISMATCH),
)
def list_all_family_tasks(
    email_parent: Optional[str] = Query(
        default=None,
        description="Parent email (`email_parent`). Optional since results are automatically filtered by the JWT token's family.",
        examples=["parent@fhk.app"],
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Task]:
    if email_parent and email_parent.lower() != current_user.email_parent.lower():
        raise AppHTTPException(error_code=ErrorCode.PARENT_EMAIL_MISMATCH)

    return (
        db.query(Task)
        .filter(Task.parent_id == current_user.id)
        .order_by(Task.created_at.desc())
        .all()
    )


@router.get(
    "/enabled",
    response_model=List[TaskResponse],
    summary="4. List family tasks with 'enable' status only",
    description=(
        "Returns only enabled tasks (`status = 'enable'`) belonging to the authenticated "
        "parent's family (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.PARENT_EMAIL_MISMATCH),
)
def list_enabled_family_tasks(
    email_parent: Optional[str] = Query(
        default=None,
        description="Parent email (`email_parent`). Optional since results are automatically filtered by the JWT token's family.",
        examples=["parent@fhk.app"],
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Task]:
    if email_parent and email_parent.lower() != current_user.email_parent.lower():
        raise AppHTTPException(error_code=ErrorCode.PARENT_EMAIL_MISMATCH)

    return (
        db.query(Task)
        .filter(
            Task.parent_id == current_user.id,
            Task.status == TaskStatusEnum.ENABLE.value,
        )
        .order_by(Task.created_at.desc())
        .all()
    )


@router.delete(
    "/{task_id}",
    response_model=TaskDeleteResponse,
    summary="5. Delete a family task",
    description=(
        "Permanently deletes a task from the database by `task_id`, verifying "
        "that it belongs to the authenticated parent's family (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.TASK_NOT_FOUND),
)
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TaskDeleteResponse:
    task = (
        db.query(Task)
        .filter(Task.id == task_id, Task.parent_id == current_user.id)
        .first()
    )
    if not task:
        raise AppHTTPException(error_code=ErrorCode.TASK_NOT_FOUND)

    deleted_task_name = task.name
    db.delete(task)
    db.commit()

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        action="DELETE_TASK",
        entity_type="tasks",
        entity_id=task_id,
        details=f"Tarea eliminada: '{deleted_task_name}'",
    )

    return TaskDeleteResponse(
        message="Tarea eliminada correctamente.",
        task_id=task_id,
    )
