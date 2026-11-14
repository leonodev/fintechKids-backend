from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.goal import Goal
from app.models.user import User
from app.schemas.goal import (
    GoalCreate,
    GoalDeleteResponse,
    GoalResponse,
    GoalStatusEnum,
    GoalUpdate,
)

router = APIRouter()


@router.post(
    "",
    response_model=GoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una nueva meta del padre (Goal)",
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
    summary="Listar metas (Goals) creadas por el padre",
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


@router.patch(
    "/{goal_id}",
    response_model=GoalResponse,
    summary="Editar una meta creada por el padre",
    description=(
        "Actualiza parcialmente `name`, `measure_type`, `value` y/o `status` (`active` / `inactive`) "
        "de una meta existente perteneciente al padre autenticado (protegido con JWT)."
    ),
)
def update_goal(
    goal_id: int,
    goal_in: GoalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Goal:
    goal = (
        db.query(Goal)
        .filter(Goal.id == goal_id, Goal.parent_id == current_user.id)
        .first()
    )
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ninguna meta de tu familia con el `goal_id` proporcionado.",
        )

    if goal_in.name is not None:
        goal.name = goal_in.name
    if goal_in.measure_type is not None:
        goal.measure_type = goal_in.measure_type
    if goal_in.value is not None:
        goal.value = goal_in.value
    if goal_in.status is not None:
        goal.status = goal_in.status.value

    goal.updated_at = datetime.now(timezone.utc)
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


@router.delete(
    "/{goal_id}",
    response_model=GoalDeleteResponse,
    summary="Eliminar una meta creada por el padre",
    description=(
        "Elimina permanentemente una meta de la base de datos buscando por su `goal_id` "
        "y verificando que pertenezca al padre autenticado (protegido con JWT)."
    ),
)
def delete_goal(
    goal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GoalDeleteResponse:
    goal = (
        db.query(Goal)
        .filter(Goal.id == goal_id, Goal.parent_id == current_user.id)
        .first()
    )
    if not goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ninguna meta de tu familia con el `goal_id` proporcionado.",
        )

    db.delete(goal)
    db.commit()

    return GoalDeleteResponse(
        message="Meta eliminada correctamente.",
        goal_id=goal_id,
    )
