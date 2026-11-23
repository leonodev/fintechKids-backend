from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, verify_parent_ownership
from app.core.audit import record_activity
from app.core.errors import AppHTTPException, ErrorCode, api_error_responses
from app.db.session import get_db
from app.models.reward import Reward
from app.models.user import User
from app.schemas.reward import (
    RewardCreate,
    RewardDeleteResponse,
    RewardResponse,
    RewardUpdate,
)

router = APIRouter()


@router.post(
    "",
    response_model=RewardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new parent reward",
    description=(
        "Registers a new reward created by the parent receiving `name`, `time_required`, "
        "`coins_required`, and `email_parent`. The `created_at` field is auto-generated in UTC "
        "and linked via foreign key (`parent_id`) to the parent account in `users` (JWT Protected)."
    ),
    responses=api_error_responses(
        ErrorCode.INVALID_OR_EXPIRED_TOKEN,
        ErrorCode.PARENT_EMAIL_NOT_FOUND,
        ErrorCode.PARENT_EMAIL_MISMATCH,
    ),
)
def create_reward(
    reward_in: RewardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Reward:
    parent_user = verify_parent_ownership(db, reward_in.email_parent, current_user)

    reward = Reward(
        name=reward_in.name,
        time_required=reward_in.time_required,
        coins_required=reward_in.coins_required,
        email_parent=parent_user.email_parent,
        parent_id=parent_user.id,
    )
    db.add(reward)
    db.commit()
    db.refresh(reward)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        action="CREATE_REWARD",
        entity_type="rewards",
        entity_id=reward.id,
        details=f"Recompensa creada: '{reward.name}' (coins_required={reward.coins_required}, time_required='{reward.time_required}')",
    )
    return reward


@router.get(
    "",
    response_model=List[RewardResponse],
    summary="List rewards created by the parent",
    description="Retrieves all rewards registered by the authenticated parent (JWT Protected).",
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.ACCOUNT_INACTIVE),
)
def list_rewards(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Reward]:
    return (
        db.query(Reward)
        .filter(Reward.parent_id == current_user.id)
        .order_by(Reward.created_at.desc())
        .all()
    )


@router.patch(
    "/{reward_id}",
    response_model=RewardResponse,
    summary="Update a reward created by the parent",
    description=(
        "Partially updates `name`, `time_required`, and/or `coins_required` of an existing reward "
        "owned by the authenticated parent (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.REWARD_NOT_FOUND),
)
def update_reward(
    reward_id: int,
    reward_in: RewardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Reward:
    reward = (
        db.query(Reward)
        .filter(Reward.id == reward_id, Reward.parent_id == current_user.id)
        .first()
    )
    if not reward:
        raise AppHTTPException(error_code=ErrorCode.REWARD_NOT_FOUND)

    if reward_in.name is not None:
        reward.name = reward_in.name
    if reward_in.time_required is not None:
        reward.time_required = reward_in.time_required
    if reward_in.coins_required is not None:
        reward.coins_required = reward_in.coins_required

    reward.updated_at = datetime.now(timezone.utc)
    db.add(reward)
    db.commit()
    db.refresh(reward)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        action="UPDATE_REWARD",
        entity_type="rewards",
        entity_id=reward.id,
        details=f"Recompensa actualizada: '{reward.name}' (coins_required={reward.coins_required}, time_required='{reward.time_required}')",
    )
    return reward


@router.delete(
    "/{reward_id}",
    response_model=RewardDeleteResponse,
    summary="Delete a reward created by the parent",
    description=(
        "Permanently deletes a reward from the database by `reward_id`, "
        "verifying ownership by the authenticated parent (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.REWARD_NOT_FOUND),
)
def delete_reward(
    reward_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RewardDeleteResponse:
    reward = (
        db.query(Reward)
        .filter(Reward.id == reward_id, Reward.parent_id == current_user.id)
        .first()
    )
    if not reward:
        raise AppHTTPException(error_code=ErrorCode.REWARD_NOT_FOUND)

    deleted_reward_name = reward.name
    db.delete(reward)
    db.commit()

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        action="DELETE_REWARD",
        entity_type="rewards",
        entity_id=reward_id,
        details=f"Recompensa eliminada: '{deleted_reward_name}'",
    )

    return RewardDeleteResponse(
        message="Recompensa eliminada correctamente.",
        reward_id=reward_id,
    )
