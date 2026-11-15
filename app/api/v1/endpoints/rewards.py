from __future__ import annotations

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.reward import Reward
from app.models.user import User
from app.schemas.reward import RewardCreate, RewardResponse

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
