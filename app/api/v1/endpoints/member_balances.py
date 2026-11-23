from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import record_activity
from app.core.errors import AppHTTPException, ErrorCode, api_error_responses
from app.db.session import get_db
from app.models.family_member import FamilyMember
from app.models.member_balance import MemberBalance
from app.models.user import User
from app.schemas.member_balance import (
    MemberBalanceCreate,
    MemberBalanceResponse,
    MemberBalanceUpdate,
)

router = APIRouter()


@router.post(
    "",
    response_model=MemberBalanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create / Register a family member's balance",
    description=(
        "Registers the coin (`coins_obtained`) and time (`time_obtained`) balance of a family member "
        "identified by `member_id` (UUID). The `created_at` field is auto-generated in UTC. "
        "If the member already has a registered balance, updates its values and returns the record (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.FAMILY_MEMBER_NOT_FOUND),
)
def create_member_balance(
    balance_in: MemberBalanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberBalance:
    member_uuid_str = str(balance_in.member_id)

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

    existing_balance = (
        db.query(MemberBalance)
        .filter(
            MemberBalance.member_id == member_uuid_str,
            MemberBalance.parent_id == current_user.id,
        )
        .first()
    )
    if existing_balance:
        existing_balance.coins_obtained = balance_in.coins_obtained
        existing_balance.time_obtained = balance_in.time_obtained
        existing_balance.updated_at = datetime.now(timezone.utc)
        db.add(existing_balance)
        db.commit()
        db.refresh(existing_balance)
        return existing_balance

    balance = MemberBalance(
        member_id=member_uuid_str,
        coins_obtained=balance_in.coins_obtained,
        time_obtained=balance_in.time_obtained,
        parent_id=current_user.id,
    )
    db.add(balance)
    db.commit()
    db.refresh(balance)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        member_id=balance.member_id,
        action="CREATE_MEMBER_BALANCE",
        entity_type="member_balances",
        entity_id=balance.member_id,
        details=f"Balance registrado: coins_obtained={balance.coins_obtained}, time_obtained='{balance.time_obtained}'",
    )
    return balance


@router.get(
    "",
    response_model=List[MemberBalanceResponse],
    summary="List balances of all family members",
    description=(
        "Retrieves the coin and time balances of all family members belonging to the authenticated parent, "
        "with an optional filter by `member_id` (UUID)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.ACCOUNT_INACTIVE),
)
def list_member_balances(
    member_id: Optional[UUID] = Query(
        default=None,
        description="Optionally filter by a specific family member's UUID",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[MemberBalance]:
    query = db.query(MemberBalance).filter(MemberBalance.parent_id == current_user.id)
    if member_id is not None:
        query = query.filter(MemberBalance.member_id == str(member_id))
    return query.order_by(MemberBalance.created_at.desc()).all()


@router.get(
    "/{member_id}",
    response_model=MemberBalanceResponse,
    summary="Get the balance of a specific family member",
    description=(
        "Returns the balance object (`coins_obtained` and `time_obtained`) of a specific family member "
        "by `member_id` (`identification_uuid`), validating that it belongs to the authenticated parent's "
        "`email_parent`. If the member exists but has no balance record yet, initializes and returns "
        "a default balance with `0` coins and `00:00:00`."
    ),
    responses=api_error_responses(
        ErrorCode.INVALID_OR_EXPIRED_TOKEN,
        ErrorCode.PARENT_EMAIL_MISMATCH,
        ErrorCode.FAMILY_MEMBER_NOT_FOUND,
    ),
)
def get_member_balance(
    member_id: UUID,
    email_parent: Optional[str] = Query(
        default=None,
        description="Parent email (`email_parent`). Optional since it is also validated automatically from the JWT token.",
        examples=["parent@fhk.app"],
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberBalance:
    if email_parent and email_parent.lower() != current_user.email_parent.lower():
        raise AppHTTPException(error_code=ErrorCode.PARENT_EMAIL_MISMATCH)

    member_uuid_str = str(member_id)
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

    balance = (
        db.query(MemberBalance)
        .filter(
            MemberBalance.member_id == member_uuid_str,
            MemberBalance.parent_id == current_user.id,
        )
        .first()
    )
    if not balance:
        # Si el miembro aún no tenía registro de saldo, se inicializa en 0 para que la app siempre reciba un balance válido
        balance = MemberBalance(
            member_id=member_uuid_str,
            coins_obtained=0,
            time_obtained="00:00:00",
            parent_id=current_user.id,
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)

    return balance


@router.patch(
    "/{member_id}",
    response_model=MemberBalanceResponse,
    summary="Update a family member's balance by UUID",
    description=(
        "Updates `coins_obtained` and/or `time_obtained` of a family member's balance "
        "identified by `member_id` (UUID) (JWT Protected)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.MEMBER_BALANCE_NOT_FOUND),
)
def update_member_balance(
    member_id: UUID,
    balance_in: MemberBalanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberBalance:
    member_uuid_str = str(member_id)
    balance = (
        db.query(MemberBalance)
        .filter(
            MemberBalance.member_id == member_uuid_str,
            MemberBalance.parent_id == current_user.id,
        )
        .first()
    )
    if not balance:
        raise AppHTTPException(error_code=ErrorCode.MEMBER_BALANCE_NOT_FOUND)

    if balance_in.coins_obtained is not None:
        balance.coins_obtained = balance_in.coins_obtained
    if balance_in.time_obtained is not None:
        balance.time_obtained = balance_in.time_obtained

    balance.updated_at = datetime.now(timezone.utc)
    db.add(balance)
    db.commit()
    db.refresh(balance)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        member_id=balance.member_id,
        action="UPDATE_MEMBER_BALANCE",
        entity_type="member_balances",
        entity_id=balance.member_id,
        details=f"Balance actualizado: coins_obtained={balance.coins_obtained}, time_obtained='{balance.time_obtained}'",
    )
    return balance
