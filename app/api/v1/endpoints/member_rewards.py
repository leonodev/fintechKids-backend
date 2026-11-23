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
from app.models.member_reward import MemberReward
from app.models.reward import Reward
from app.models.user import User
from app.schemas.member_reward import (
    MemberRewardCreate,
    MemberRewardDeleteResponse,
    MemberRewardResponse,
    MemberRewardStateEnum,
    MemberRewardUpdate,
)

router = APIRouter()


@router.post(
    "",
    response_model=MemberRewardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a reward claimed by a family member",
    description=(
        "Registers a reward selected by a family member with initial state `PENDING`. "
        "You can send `reward_id` so the backend automatically resolves `name_reward` by matching it "
        "against the parent's `rewards` table, or send `name_reward` directly (JWT Protected)."
    ),
    responses=api_error_responses(
        ErrorCode.INVALID_OR_EXPIRED_TOKEN,
        ErrorCode.PARENT_EMAIL_NOT_FOUND,
        ErrorCode.PARENT_EMAIL_MISMATCH,
        ErrorCode.FAMILY_MEMBER_NOT_FOUND,
        ErrorCode.REWARD_NOT_FOUND,
        ErrorCode.REWARD_NAME_OR_ID_REQUIRED,
    ),
)
def create_member_reward(
    member_reward_in: MemberRewardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberReward:
    # 1. Validate parent_email exists and matches authenticated parent
    parent_user = verify_parent_ownership(db, member_reward_in.parent_email, current_user)

    # 2. Validate member_id (UUID) exists and belongs to this family
    member_uuid_str = str(member_reward_in.member_id)
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

    # 3. Resolve name_reward from reward_id (if provided) or use direct name_reward
    resolved_name_reward = member_reward_in.name_reward
    resolved_reward_id = member_reward_in.reward_id

    if resolved_reward_id is not None:
        parent_reward = (
            db.query(Reward)
            .filter(Reward.id == resolved_reward_id, Reward.parent_id == current_user.id)
            .first()
        )
        if not parent_reward:
            raise AppHTTPException(error_code=ErrorCode.REWARD_NOT_FOUND)
        if not resolved_name_reward:
            resolved_name_reward = parent_reward.name

    if not resolved_name_reward:
        raise AppHTTPException(error_code=ErrorCode.REWARD_NAME_OR_ID_REQUIRED)

    member_reward = MemberReward(
        reward_id=resolved_reward_id,
        member_id=member_uuid_str,
        parent_email=parent_user.email_parent,
        name_reward=resolved_name_reward,
        claimed_value=member_reward_in.claimed_value,
        state=member_reward_in.state.value,
        parent_id=parent_user.id,
    )
    db.add(member_reward)
    db.commit()
    db.refresh(member_reward)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        member_id=member_reward.member_id,
        action="CLAIM_MEMBER_REWARD",
        entity_type="member_rewards",
        entity_id=member_reward.id,
        details=f"Recompensa reclamada: '{member_reward.name_reward}' (claimed_value='{member_reward.claimed_value}', state={member_reward.state})",
    )
    return member_reward


@router.get(
    "",
    response_model=List[MemberRewardResponse],
    summary="List claimed/collected member rewards",
    description=(
        "Retrieves rewards claimed by family members, with optional filters "
        "by `member_id` (UUID) and `state` (`PENDING` or `COLLECTED`) (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.ACCOUNT_INACTIVE),
)
def list_member_rewards(
    member_id: Optional[UUID] = Query(
        default=None,
        description="Optionally filter by a specific family member's UUID",
    ),
    state: Optional[MemberRewardStateEnum] = Query(
        default=None,
        description="Optionally filter by state (`PENDING` or `COLLECTED`)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[MemberReward]:
    query = db.query(MemberReward).filter(MemberReward.parent_id == current_user.id)
    if member_id is not None:
        query = query.filter(MemberReward.member_id == str(member_id))
    if state is not None:
        query = query.filter(MemberReward.state == state.value)
    return query.order_by(MemberReward.created_at.desc()).all()


@router.patch(
    "/{member_reward_id}",
    response_model=MemberRewardResponse,
    summary="Update claimed reward state (from PENDING to COLLECTED)",
    description=(
        "Allows the parent to change the `state` of a claimed reward (for example, from `PENDING` to "
        "`COLLECTED` once the reward has been delivered to the family member) (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.MEMBER_REWARD_NOT_FOUND),
)
def update_member_reward_state(
    member_reward_id: int,
    update_in: MemberRewardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberReward:
    member_reward = (
        db.query(MemberReward)
        .filter(
            MemberReward.id == member_reward_id,
            MemberReward.parent_id == current_user.id,
        )
        .first()
    )
    if not member_reward:
        raise AppHTTPException(error_code=ErrorCode.MEMBER_REWARD_NOT_FOUND)

    member_reward.state = update_in.state.value
    if update_in.claimed_value is not None:
        member_reward.claimed_value = update_in.claimed_value

    member_reward.updated_at = datetime.now(timezone.utc)
    db.add(member_reward)
    db.commit()
    db.refresh(member_reward)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        member_id=member_reward.member_id,
        action="UPDATE_MEMBER_REWARD_STATE",
        entity_type="member_rewards",
        entity_id=member_reward.id,
        details=f"Estado de recompensa '{member_reward.name_reward}' cambiado a {member_reward.state}",
    )
    return member_reward


@router.delete(
    "/{member_reward_id}",
    response_model=MemberRewardDeleteResponse,
    summary="Delete a claimed/collected member reward",
    description=(
        "Permanently deletes a claimed/collected reward by `member_reward_id`, "
        "verifying ownership by the authenticated parent (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.MEMBER_REWARD_NOT_FOUND),
)
def delete_member_reward(
    member_reward_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberRewardDeleteResponse:
    member_reward = (
        db.query(MemberReward)
        .filter(
            MemberReward.id == member_reward_id,
            MemberReward.parent_id == current_user.id,
        )
        .first()
    )
    if not member_reward:
        raise AppHTTPException(error_code=ErrorCode.MEMBER_REWARD_NOT_FOUND)

    deleted_member_id = member_reward.member_id
    deleted_reward_name = member_reward.name_reward
    db.delete(member_reward)
    db.commit()

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        member_id=deleted_member_id,
        action="DELETE_MEMBER_REWARD",
        entity_type="member_rewards",
        entity_id=member_reward_id,
        details=f"Recompensa reclamada eliminada: '{deleted_reward_name}'",
    )

    return MemberRewardDeleteResponse(
        message="Recompensa reclamada eliminada correctamente.",
        member_reward_id=member_reward_id,
    )
