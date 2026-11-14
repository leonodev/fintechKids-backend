from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Obtener datos de la familia / padre autenticado",
    description="Devuelve la información registrada de la familia propietaria del token JWT actual.",
)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Actualizar datos de la familia / padre autenticado",
    description="Permite actualizar `name_family`, `password` o `approve_pin` de la cuenta autenticada.",
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
    return current_user
