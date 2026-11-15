from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import record_activity
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
)
def create_goal(
    goal_in: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Goal:
    parent_user = db.query(User).filter(User.email_parent == goal_in.email_parent.lower()).first()
    if not parent_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró una familia registrada con el correo `email_parent` indicado.",
        )

    if parent_user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El `email_parent` enviado no corresponde al usuario autenticado en el token JWT.",
        )

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ninguna meta de tu familia con el `goal_id` proporcionado.",
        )

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ninguna meta de tu familia con el `goal_id` proporcionado.",
        )

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
