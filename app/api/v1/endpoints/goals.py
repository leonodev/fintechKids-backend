from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, verify_parent_ownership
from app.core.audit import record_activity
from app.core.errors import AppHTTPException, ErrorCode, api_error_responses
from app.db.session import get_db
from app.models.goal import Goal
from app.models.user import User
from app.schemas.goal import (
    GoalCreate,
    GoalDeleteResponse,
    GoalResponse,
    GoalStatusEnum,
    GoalUpdate,
)

router = APIRouter()


@router.post(
    "",
    response_model=GoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new parent goal",
    description=(
        "Registers a new goal in the database receiving `measure_type`, `status` (`active` or `inactive`), "
        "`email_parent`, `name`, and `value` (Int). The `created_at` field is auto-generated in UTC and "
        "linked via foreign key (`parent_id`) to the parent account in `users` (JWT Protected)."
    ),
    responses=api_error_responses(
        ErrorCode.INVALID_OR_EXPIRED_TOKEN,
        ErrorCode.PARENT_EMAIL_NOT_FOUND,
        ErrorCode.PARENT_EMAIL_MISMATCH,
    ),
)
def create_goal(
    goal_in: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Goal:
    parent_user = verify_parent_ownership(db, goal_in.email_parent, current_user)

    goal = Goal(
        measure_type=goal_in.measure_type,
        status=goal_in.status.value,
        email_parent=parent_user.email_parent,
        name=goal_in.name,
        value=goal_in.value,
        parent_id=parent_user.id,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        action="CREATE_GOAL",
        entity_type="goals",
        entity_id=goal.id,
        details=f"Meta creada: '{goal.name}' ({goal.value} {goal.measure_type}, status={goal.status})",
    )
    return goal


@router.get(
    "",
    response_model=List[GoalResponse],
    summary="List goals created by the parent",
    description="Retrieves all goals registered by the authenticated parent, with an optional filter by `status`.",
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.ACCOUNT_INACTIVE),
)
def list_goals(
    goal_status: Optional[GoalStatusEnum] = Query(
        default=None,
        alias="status",
        description="Optionally filter by goal status (`active` or `inactive`)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Goal]:
    query = db.query(Goal).filter(Goal.parent_id == current_user.id)
    if goal_status is not None:
        query = query.filter(Goal.status == goal_status.value)
    return query.order_by(Goal.created_at.desc()).all()


@router.patch(
    "/{goal_id}",
    response_model=GoalResponse,
    summary="Update a goal created by the parent",
    description=(
        "Partially updates `name`, `measure_type`, `value`, and/or `status` (`active` / `inactive`) "
        "of an existing goal owned by the authenticated parent (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.GOAL_NOT_FOUND),
)
def update_goal(
    goal_id: int,
    goal_in: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Goal:
    goal = (
        db.query(Goal)
        .filter(Goal.id == goal_id, Goal.parent_id == current_user.id)
        .first()
    )
    if not goal:
        raise AppHTTPException(error_code=ErrorCode.GOAL_NOT_FOUND)

    if goal_in.name is not None:
        goal.name = goal_in.name
    if goal_in.measure_type is not None:
        goal.measure_type = goal_in.measure_type
    if goal_in.value is not None:
        goal.value = goal_in.value
    if goal_in.status is not None:
        goal.status = goal_in.status.value

    goal.updated_at = datetime.now(timezone.utc)
    db.add(goal)
    db.commit()
    db.refresh(goal)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        action="UPDATE_GOAL",
        entity_type="goals",
        entity_id=goal.id,
        details=f"Meta actualizada: '{goal.name}' ({goal.value} {goal.measure_type}, status={goal.status})",
    )
    return goal


@router.delete(
    "/{goal_id}",
    response_model=GoalDeleteResponse,
    summary="Delete a goal created by the parent",
    description=(
        "Permanently deletes a goal from the database by `goal_id`, "
        "verifying ownership by the authenticated parent (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.GOAL_NOT_FOUND),
)
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalDeleteResponse:
    goal = (
        db.query(Goal)
        .filter(Goal.id == goal_id, Goal.parent_id == current_user.id)
        .first()
    )
    if not goal:
        raise AppHTTPException(error_code=ErrorCode.GOAL_NOT_FOUND)

    deleted_goal_name = goal.name
    db.delete(goal)
    db.commit()

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        action="DELETE_GOAL",
        entity_type="goals",
        entity_id=goal_id,
        details=f"Meta eliminada: '{deleted_goal_name}'",
    )

    return GoalDeleteResponse(
        message="Meta eliminada correctamente.",
        goal_id=goal_id,
    )
