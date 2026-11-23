from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, verify_parent_ownership
from app.core.audit import record_activity
from app.core.errors import AppHTTPException, ErrorCode, api_error_responses
from app.db.session import get_db
from app.models.family_member import FamilyMember
from app.models.goal import Goal
from app.models.member_goal import MemberGoal
from app.models.user import User
from app.schemas.member_goal import (
    MemberGoalCreate,
    MemberGoalDeleteResponse,
    MemberGoalResponse,
    MemberGoalUpdate,
)

router = APIRouter()


@router.post(
    "",
    response_model=MemberGoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign / Create a goal for a family member",
    description=(
        "Registers a goal selected by a family member based on a goal created by the parent. "
        "Receives `goal_id`, `member_id` (UUID), `rewards_system_type`, `rewards_system_value`, "
        "`accumulated_value`, `parent_email`, and `name`. The `created_at` field is auto-generated in UTC "
        "and relational integrity with the parent, base goal, and family member is validated (JWT Protected)."
    ),
    responses=api_error_responses(
        ErrorCode.INVALID_OR_EXPIRED_TOKEN,
        ErrorCode.PARENT_EMAIL_NOT_FOUND,
        ErrorCode.PARENT_EMAIL_MISMATCH,
        ErrorCode.GOAL_NOT_FOUND,
        ErrorCode.FAMILY_MEMBER_NOT_FOUND,
    ),
)
def create_member_goal(
    member_goal_in: MemberGoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberGoal:
    # 1. Validate parent_email exists and matches authenticated parent
    parent_user = verify_parent_ownership(db, member_goal_in.parent_email, current_user)

    # 2. Validate goal_id exists and belongs to this family
    parent_goal = (
        db.query(Goal)
        .filter(Goal.id == member_goal_in.goal_id, Goal.parent_id == current_user.id)
        .first()
    )
    if not parent_goal:
        raise AppHTTPException(error_code=ErrorCode.GOAL_NOT_FOUND)

    # 3. Validate member_id (UUID) exists and belongs to this family
    member_uuid_str = str(member_goal_in.member_id)
    family_member = (
        db.query(FamilyMember)
        .filter(
            FamilyMember.identification_uuid == member_uuid_str,
            FamilyMember.parent_id == current_user.id,
        )
        .first()
    )
    if not family_member:
        raise AppHTTPException(error_code=ErrorCode.FAMILY_MEMBER_NOT_FOUND)

    member_goal = MemberGoal(
        goal_id=parent_goal.id,
        member_id=member_uuid_str,
        rewards_system_type=member_goal_in.rewards_system_type,
        rewards_system_value=member_goal_in.rewards_system_value,
        accumulated_value=member_goal_in.accumulated_value,
        parent_email=parent_user.email_parent,
        name=member_goal_in.name,
        parent_id=parent_user.id,
    )
    db.add(member_goal)
    db.commit()
    db.refresh(member_goal)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        member_id=member_goal.member_id,
        action="CREATE_MEMBER_GOAL",
        entity_type="member_goals",
        entity_id=member_goal.id,
        details=f"Meta asignada a miembro: '{member_goal.name}' (accumulated_value={member_goal.accumulated_value})",
    )
    return member_goal


@router.get(
    "",
    response_model=List[MemberGoalResponse],
    summary="List family member goals",
    description=(
        "Retrieves all goals assigned to family members of the authenticated parent, "
        "with optional filters by `member_id` (UUID) or `goal_id`."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.ACCOUNT_INACTIVE),
)
def list_member_goals(
    member_id: Optional[UUID] = Query(
        default=None,
        description="Optionally filter by a specific family member's UUID",
    ),
    goal_id: Optional[int] = Query(
        default=None,
        description="Optionally filter by the parent's base goal ID",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[MemberGoal]:
    query = db.query(MemberGoal).filter(MemberGoal.parent_id == current_user.id)
    if member_id is not None:
        query = query.filter(MemberGoal.member_id == str(member_id))
    if goal_id is not None:
        query = query.filter(MemberGoal.goal_id == goal_id)
    return query.order_by(MemberGoal.created_at.desc()).all()


@router.patch(
    "/{member_goal_id}",
    response_model=MemberGoalResponse,
    summary="Update progress (accumulated_value) or details of a member goal",
    description=(
        "Updates the progress (`accumulated_value`) and optionally the name or reward settings "
        "of a member's goal identified by `member_goal_id` (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.MEMBER_GOAL_NOT_FOUND),
)
def update_member_goal(
    member_goal_id: int,
    member_goal_in: MemberGoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberGoal:
    member_goal = (
        db.query(MemberGoal)
        .filter(
            MemberGoal.id == member_goal_id,
            MemberGoal.parent_id == current_user.id,
        )
        .first()
    )
    if not member_goal:
        raise AppHTTPException(error_code=ErrorCode.MEMBER_GOAL_NOT_FOUND)

    if member_goal_in.accumulated_value is not None:
        member_goal.accumulated_value = member_goal_in.accumulated_value
    if member_goal_in.rewards_system_type is not None:
        member_goal.rewards_system_type = member_goal_in.rewards_system_type
    if member_goal_in.rewards_system_value is not None:
        member_goal.rewards_system_value = member_goal_in.rewards_system_value
    if member_goal_in.name is not None:
        member_goal.name = member_goal_in.name

    member_goal.updated_at = datetime.now(timezone.utc)
    db.add(member_goal)
    db.commit()
    db.refresh(member_goal)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        member_id=member_goal.member_id,
        action="UPDATE_MEMBER_GOAL",
        entity_type="member_goals",
        entity_id=member_goal.id,
        details=f"Progreso de meta actualizado: '{member_goal.name}' (accumulated_value={member_goal.accumulated_value})",
    )
    return member_goal


@router.delete(
    "/{member_goal_id}",
    response_model=MemberGoalDeleteResponse,
    summary="Delete a family member's goal",
    description=(
        "Permanently deletes a goal assigned to a family member by `member_goal_id`, "
        "verifying ownership by the authenticated parent (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.MEMBER_GOAL_NOT_FOUND),
)
def delete_member_goal(
    member_goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberGoalDeleteResponse:
    member_goal = (
        db.query(MemberGoal)
        .filter(
            MemberGoal.id == member_goal_id,
            MemberGoal.parent_id == current_user.id,
        )
        .first()
    )
    if not member_goal:
        raise AppHTTPException(error_code=ErrorCode.MEMBER_GOAL_NOT_FOUND)

    deleted_member_id = member_goal.member_id
    deleted_goal_name = member_goal.name
    db.delete(member_goal)
    db.commit()

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        member_id=deleted_member_id,
        action="DELETE_MEMBER_GOAL",
        entity_type="member_goals",
        entity_id=member_goal_id,
        details=f"Meta de miembro eliminada: '{deleted_goal_name}'",
    )

    return MemberGoalDeleteResponse(
        message="Meta del miembro eliminada correctamente.",
        member_goal_id=member_goal_id,
    )
