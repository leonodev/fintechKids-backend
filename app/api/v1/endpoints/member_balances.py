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
    summary="Registrar / Crear el balance de un miembro de la familia",
    description=(
        "Registra el balance de monedas (`coins_obtained`) y tiempo (`time_obtained`) de un miembro "
        "identificado por `member_id` (UUID). El campo `created_at` se asigna automáticamente en UTC. "
        "Si el miembro ya tenía un balance registrado, actualiza sus valores y devuelve el registro "
        "(protegido con JWT)."
    ),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ningún miembro en tu familia con el `member_id` (UUID) indicado.",
        )

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
    summary="Listar balances de los miembros de la familia",
    description=(
        "Obtiene los balances de monedas y tiempo de todos los miembros de la familia del padre autenticado, "
        "con filtro opcional por `member_id` (UUID)."
    ),
)
def list_member_balances(
    member_id: Optional[UUID] = Query(
        default=None,
        description="Filtrar opcionalmente por el UUID de un miembro específico",
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
    summary="Obtener el saldo (balance) de un miembro en concreto",
    description=(
        "Devuelve el objeto de balance (`coins_obtained` y `time_obtained`) de un miembro específico "
        "buscando por su `member_id` (`identification_uuid`) y validando que pertenezca al `email_parent` "
        "del padre autenticado en el token JWT. Si el miembro existe pero aún no tenía saldo registrado, "
        "inicializa y retorna su balance en `0` monedas y `00:00:00`."
    ),
)
def get_member_balance(
    member_id: UUID,
    email_parent: Optional[str] = Query(
        default=None,
        description="Correo del padre (`email_parent`). Opcional ya que también se valida automáticamente desde el token JWT.",
        examples=["padre@fhk.app"],
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberBalance:
    if email_parent and email_parent.lower() != current_user.email_parent.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El `email_parent` enviado no corresponde al usuario autenticado en el token JWT.",
        )

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ningún miembro en tu familia con el `member_id` (UUID) indicado.",
        )

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
    summary="Actualizar el balance de un miembro por su UUID",
    description=(
        "Actualiza `coins_obtained` y/o `time_obtained` del balance de un miembro "
        "identificado por su `member_id` (UUID) (protegido con JWT)."
    ),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró un balance registrado para el `member_id` proporcionado.",
        )

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
