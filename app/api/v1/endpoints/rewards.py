from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.audit import record_activity
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
    summary="Crear una nueva recompensa del padre (Reward)",
    description=(
        "Registra una nueva recompensa creada por el padre recibiendo `name`, `time_required` "
        "(también acepta `time_requiered`), `coins_required` y `email_parent`. El campo `created_at` "
        "se asigna automáticamente en UTC y se relaciona por llave foránea (`parent_id`) con la "
        "cuenta del padre en `users` (protegido con JWT)."
    ),
)
def create_reward(
    reward_in: RewardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Reward:
    parent_user = db.query(User).filter(User.email_parent == reward_in.email_parent.lower()).first()
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
    summary="Listar recompensas (Rewards) creadas por el padre",
    description="Obtiene todas las recompensas registradas por el padre autenticado (protegido con JWT).",
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
    summary="Editar una recompensa creada por el padre",
    description=(
        "Actualiza parcialmente `name`, `time_required` y/o `coins_required` de una recompensa "
        "existente perteneciente al padre autenticado (protegido con JWT)."
    ),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ninguna recompensa en tu familia con el `reward_id` proporcionado.",
        )

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
    summary="Eliminar una recompensa creada por el padre",
    description=(
        "Elimina permanentemente una recompensa de la base de datos buscando por su `reward_id` "
        "y verificando que pertenezca al padre autenticado (protegido con JWT)."
    ),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ninguna recompensa en tu familia con el `reward_id` proporcionado.",
        )

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
