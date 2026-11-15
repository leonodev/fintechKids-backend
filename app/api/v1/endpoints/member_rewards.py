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
    summary="Registrar una recompensa reclamada por un miembro de la familia",
    description=(
        "Registra una recompensa seleccionada por un miembro de la familia con estado inicial `PENDING`. "
        "Puedes enviar `reward_id` para que el backend resuelva automáticamente `name_reward` cruzándolo "
        "con la tabla `rewards` del padre, o enviar `name_reward` directamente (protegido con JWT)."
    ),
)
def create_member_reward(
    member_reward_in: MemberRewardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberReward:
    # 1. Validar que parent_email exista y corresponda al padre autenticado
    parent_user = db.query(User).filter(User.email_parent == member_reward_in.parent_email.lower()).first()
    if not parent_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró una familia registrada con el correo `parent_email` indicado.",
        )

    if parent_user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El `parent_email` enviado no corresponde al usuario autenticado en el token JWT.",
        )

    # 2. Validar que el miembro (member_id UUID) exista y pertenezca a esta familia
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ningún miembro en tu familia con el `member_id` (UUID) indicado.",
        )

    # 3. Resolver name_reward desde reward_id (si fue enviado) o usar name_reward directo
    resolved_name_reward = member_reward_in.name_reward
    resolved_reward_id = member_reward_in.reward_id

    if resolved_reward_id is not None:
        parent_reward = (
            db.query(Reward)
            .filter(Reward.id == resolved_reward_id, Reward.parent_id == current_user.id)
            .first()
        )
        if not parent_reward:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontró ninguna recompensa del padre con el `reward_id` indicado.",
            )
        if not resolved_name_reward:
            resolved_name_reward = parent_reward.name

    if not resolved_name_reward:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debes enviar `reward_id` (para resolver el nombre automáticamente) o `name_reward`.",
        )

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
    summary="Listar recompensas reclamadas/cobradas por los miembros",
    description=(
        "Obtiene las recompensas reclamadas por los miembros de la familia, con filtros opcionales "
        "por `member_id` (UUID) y `state` (`PENDING` o `COLLECTED`) (protegido con JWT)."
    ),
)
def list_member_rewards(
    member_id: Optional[UUID] = Query(
        default=None,
        description="Filtrar opcionalmente por el UUID de un miembro específico",
    ),
    state: Optional[MemberRewardStateEnum] = Query(
        default=None,
        description="Filtrar opcionalmente por estado (`PENDING` o `COLLECTED`)",
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
    summary="Cambiar estado de la recompensa (de PENDING a COLLECTED)",
    description=(
        "Permite al padre cambiar el `state` de una recompensa reclamada (por ejemplo, de `PENDING` a "
        "`COLLECTED` cuando ya entregó la recompensa al miembro) (protegido con JWT)."
    ),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ninguna recompensa reclamada con el `member_reward_id` proporcionado.",
        )

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
    summary="Eliminar una recompensa reclamada/cobrada de un miembro",
    description=(
        "Elimina permanentemente una recompensa reclamada/cobrada buscando por `member_reward_id` "
        "y verificando que pertenezca al padre autenticado (protegido con JWT)."
    ),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ninguna recompensa reclamada con el `member_reward_id` proporcionado.",
        )

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
