from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import record_activity
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


@router.patch(
    "/{identification_uuid}",
    response_model=FamilyMemberResponse,
    summary="Editar nombre o avatar de un miembro de la familia",
    description=(
        "Actualiza el nombre (`member_name`) y/o el avatar (`avatar_name`) de un miembro de la familia "
        "identificado por su `identification_uuid` (protegido con JWT)."
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ningún miembro de tu familia con el `identification_uuid` proporcionado.",
        )

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
    summary="Eliminar un miembro de la familia",
    description=(
        "Elimina permanentemente un miembro de la familia de la base de datos buscando por su "
        "`identification_uuid` y verificando que pertenezca al padre autenticado (protegido con JWT)."
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ningún miembro de tu familia con el `identification_uuid` proporcionado.",
        )

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
