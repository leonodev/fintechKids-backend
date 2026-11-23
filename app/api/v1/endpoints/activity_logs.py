from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import ErrorCode, api_error_responses
from app.db.session import get_db
from app.models.activity_log import ActivityLog
from app.models.user import User
from app.schemas.activity_log import ActivityLogResponse

router = APIRouter()


@router.get(
    "",
    response_model=List[ActivityLogResponse],
    summary="Query the family's activity history (Audit Log)",
    description=(
        "Returns the historical audit trail of actions automatically recorded by the backend "
        "for the authenticated parent's family, ordered from newest to oldest. "
        "Supports optional filtering by `member_id`, `entity_type`, or `action` (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.ACCOUNT_INACTIVE),
)
def list_activity_logs(
    member_id: Optional[str] = Query(
        default=None,
        description="Optionally filter by a family member's UUID",
    ),
    entity_type: Optional[str] = Query(
        default=None,
        description="Filter by module/entity (`users`, `family_members`, `goals`, `member_goals`, `member_balances`, `rewards`, `member_rewards`, `tasks`)",
    ),
    action: Optional[str] = Query(
        default=None,
        description="Filter by action type (e.g. `CREATE_TASK`, `UPDATE_MEMBER_BALANCE`, `CLAIM_MEMBER_REWARD`)",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of historical events to return",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ActivityLog]:
    query = db.query(ActivityLog).filter(ActivityLog.parent_id == current_user.id)
    if member_id:
        query = query.filter(ActivityLog.member_id == member_id)
    if entity_type:
        query = query.filter(ActivityLog.entity_type == entity_type)
    if action:
        query = query.filter(ActivityLog.action == action)

    return query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(limit).all()
