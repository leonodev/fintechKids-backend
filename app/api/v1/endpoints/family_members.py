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
from app.models.user import User
from app.schemas.family_member import (
    FamilyMemberCreate,
    FamilyMemberDeleteResponse,
    FamilyMemberResponse,
    FamilyMemberUpdate,
)

router = APIRouter()


@router.post(
    "",
    response_model=FamilyMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new family member",
    description=(
        "Registers a new family member receiving `email_parent`, `identification_uuid` (UUID), "
        "`member_name`, `avatar_name`, and `name_family`. Linked via foreign key (`parent_id`) "
        "to the parent account in `users` (JWT Protected)."
    ),
    responses=api_error_responses(
        ErrorCode.INVALID_OR_EXPIRED_TOKEN,
        ErrorCode.PARENT_EMAIL_NOT_FOUND,
        ErrorCode.PARENT_EMAIL_MISMATCH,
        ErrorCode.FAMILY_MEMBER_ALREADY_EXISTS,
    ),
)
def create_family_member(
    member_in: FamilyMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilyMember:
    parent_user = verify_parent_ownership(db, member_in.email_parent, current_user)

    uuid_str = str(member_in.identification_uuid)
    existing_member = (
        db.query(FamilyMember)
        .filter(FamilyMember.identification_uuid == uuid_str)
        .first()
    )
    if existing_member:
        raise AppHTTPException(error_code=ErrorCode.FAMILY_MEMBER_ALREADY_EXISTS)

    member = FamilyMember(
        identification_uuid=uuid_str,
        email_parent=parent_user.email_parent,
        name_family=member_in.name_family,
        member_name=member_in.member_name,
        avatar_name=member_in.avatar_name,
        parent_id=parent_user.id,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        member_id=member.identification_uuid,
        action="CREATE_MEMBER",
        entity_type="family_members",
        entity_id=member.identification_uuid,
        details=f"Miembro creado: '{member.member_name}' (avatar='{member.avatar_name}')",
    )
    return member


@router.get(
    "",
    response_model=List[FamilyMemberResponse],
    summary="List family members",
    description="Retrieves all registered family members belonging to the authenticated parent.",
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.ACCOUNT_INACTIVE),
)
def list_family_members(
    email_parent: Optional[str] = Query(
        default=None,
        description="Optional filter by `email_parent` (defaults to the email in the current JWT token)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[FamilyMember]:
    query = db.query(FamilyMember).filter(FamilyMember.parent_id == current_user.id)
    if email_parent:
        query = query.filter(FamilyMember.email_parent == email_parent.lower())
    return query.order_by(FamilyMember.created_at.asc()).all()


@router.patch(
    "/{identification_uuid}",
    response_model=FamilyMemberResponse,
    summary="Update a family member's name or avatar",
    description=(
        "Updates `member_name` and/or `avatar_name` of a family member "
        "identified by `identification_uuid` (JWT Protected)."
    ),
    responses=api_error_responses(
        ErrorCode.INVALID_OR_EXPIRED_TOKEN,
        ErrorCode.FAMILY_MEMBER_NOT_FOUND,
    ),
)
def update_family_member(
    identification_uuid: UUID,
    member_in: FamilyMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilyMember:
    uuid_str = str(identification_uuid)
    member = (
        db.query(FamilyMember)
        .filter(
            FamilyMember.identification_uuid == uuid_str,
            FamilyMember.parent_id == current_user.id,
        )
        .first()
    )
    if not member:
        raise AppHTTPException(error_code=ErrorCode.FAMILY_MEMBER_NOT_FOUND)

    if member_in.member_name is not None:
        member.member_name = member_in.member_name
    if member_in.avatar_name is not None:
        member.avatar_name = member_in.avatar_name

    member.updated_at = datetime.now(timezone.utc)
    db.add(member)
    db.commit()
    db.refresh(member)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        member_id=member.identification_uuid,
        action="UPDATE_MEMBER",
        entity_type="family_members",
        entity_id=member.identification_uuid,
        details=f"Miembro actualizado: '{member.member_name}' (avatar='{member.avatar_name}')",
    )
    return member


@router.delete(
    "/{identification_uuid}",
    response_model=FamilyMemberDeleteResponse,
    summary="Delete a family member",
    description=(
        "Permanently deletes a family member from the database by `identification_uuid`, "
        "verifying ownership by the authenticated parent (JWT Protected)."
    ),
    responses=api_error_responses(
        ErrorCode.INVALID_OR_EXPIRED_TOKEN,
        ErrorCode.FAMILY_MEMBER_NOT_FOUND,
    ),
)
def delete_family_member(
    identification_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilyMemberDeleteResponse:
    uuid_str = str(identification_uuid)
    member = (
        db.query(FamilyMember)
        .filter(
            FamilyMember.identification_uuid == uuid_str,
            FamilyMember.parent_id == current_user.id,
        )
        .first()
    )
    if not member:
        raise AppHTTPException(error_code=ErrorCode.FAMILY_MEMBER_NOT_FOUND)

    deleted_name = member.member_name
    db.delete(member)
    db.commit()

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        member_id=uuid_str,
        action="DELETE_MEMBER",
        entity_type="family_members",
        entity_id=uuid_str,
        details=f"Miembro eliminado: '{deleted_name}'",
    )

    return FamilyMemberDeleteResponse(
        message="Miembro de la familia eliminado correctamente.",
        identification_uuid=identification_uuid,
    )
