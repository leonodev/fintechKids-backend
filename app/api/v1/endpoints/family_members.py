from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.family_member import FamilyMember
from app.models.user import User
from app.schemas.family_member import FamilyMemberCreate, FamilyMemberResponse

router = APIRouter()


@router.post(
    "",
    response_model=FamilyMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo miembro de la familia",
    description=(
        "Registra un nuevo miembro en la familia recibiendo `email_parent`, `identification_uuid` (UUID), "
        "`member_name`, `avatar_name` y `name_family`. Se vincula por llave foránea (`parent_id`) con la "
        "cuenta del padre registrada en `users` (protegido con JWT)."
    ),
)
def create_family_member(
    member_in: FamilyMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> FamilyMember:
    parent_user = db.query(User).filter(User.email_parent == member_in.email_parent.lower()).first()
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

    uuid_str = str(member_in.identification_uuid)
    existing_member = (
        db.query(FamilyMember)
        .filter(FamilyMember.identification_uuid == uuid_str)
        .first()
    )
    if existing_member:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un miembro de la familia registrado con este `identification_uuid`.",
        )

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
    return member


@router.get(
    "",
    response_model=List[FamilyMemberResponse],
    summary="Listar miembros de la familia",
    description="Obtiene todos los miembros registrados de la familia del padre autenticado.",
)
def list_family_members(
    email_parent: Optional[str] = Query(
        default=None,
        description="Filtro opcional por `email_parent` (por defecto usa el del token JWT actual)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[FamilyMember]:
    query = db.query(FamilyMember).filter(FamilyMember.parent_id == current_user.id)
    if email_parent:
        query = query.filter(FamilyMember.email_parent == email_parent.lower())
    return query.order_by(FamilyMember.created_at.asc()).all()
