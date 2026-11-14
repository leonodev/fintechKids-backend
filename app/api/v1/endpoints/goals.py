from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.goal import Goal
from app.models.user import User
from app.schemas.goal import GoalCreate, GoalResponse, GoalStatusEnum

router = APIRouter()


@router.post(
    "",
    response_model=GoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva meta (Goal)",
    description=(
        "Registra una nueva meta en la base de datos recibiendo `measure_type`, `status` (`active` o `inactive`), "
        "`email_parent`, `name` y `value` (Int). El campo `created_at` se asigna automáticamente en UTC y "
        "se relaciona por llave foránea (`parent_id`) con la cuenta del padre en `users` (protegido con JWT)."
    ),
)
def create_goal(
    goal_in: GoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Goal:
    parent_user = db.query(User).filter(User.email_parent == goal_in.email_parent.lower()).first()
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

    goal = Goal(
        measure_type=goal_in.measure_type,
        status=goal_in.status.value,
        email_parent=parent_user.email_parent,
        name=goal_in.name,
        value=goal_in.value,
        parent_id=parent_user.id,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.get(
    "",
    response_model=List[GoalResponse],
    summary="Listar metas (Goals) de la familia",
    description="Obtiene todas las metas registradas por el padre autenticado, con filtro opcional por `status`.",
)
def list_goals(
    goal_status: Optional[GoalStatusEnum] = Query(
        default=None,
        alias="status",
        description="Filtrar opcionalmente por estado (`active` o `inactive`)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Goal]:
    query = db.query(Goal).filter(Goal.parent_id == current_user.id)
    if goal_status is not None:
        query = query.filter(Goal.status == goal_status.value)
    return query.order_by(Goal.created_at.desc()).all()
