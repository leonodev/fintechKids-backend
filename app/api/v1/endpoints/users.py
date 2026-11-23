from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import record_activity
from app.core.errors import ErrorCode, api_error_responses
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get authenticated family / parent profile",
    description="Returns the registered profile information for the family that owns the current JWT token.",
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.ACCOUNT_INACTIVE),
)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update authenticated family / parent profile",
    description="Updates `name_family`, `password`, or `approve_pin` for the authenticated family account.",
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.ACCOUNT_INACTIVE),
)
def update_current_user(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    if user_in.name_family is not None:
        current_user.name_family = user_in.name_family
        # Mantener sincronizado name_family en todos los miembros de la familia asociados
        for member in current_user.family_members:
            member.name_family = user_in.name_family
    if user_in.password is not None:
        current_user.hashed_password = get_password_hash(user_in.password)
    if user_in.approve_pin is not None:
        current_user.approve_pin = user_in.approve_pin

    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    record_activity(
        db,
        parent_id=current_user.id,
        email_parent=current_user.email_parent,
        action="UPDATE_FAMILY_PROFILE",
        entity_type="users",
        entity_id=current_user.id,
        details=f"Perfil familiar actualizado (name_family='{current_user.name_family}')",
    )
    return current_user
