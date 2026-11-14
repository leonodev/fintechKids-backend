from __future__ import annotations

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.family_member import FamilyMember
from app.models.goal import Goal
from app.models.member_goal import MemberGoal
from app.models.user import User
from app.schemas.member_goal import MemberGoalCreate, MemberGoalResponse

router = APIRouter()


@router.post(
    "",
    response_model=MemberGoalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Asignar / Crear una meta para un miembro de la familia",
    description=(
        "Registra una meta seleccionada por un miembro de la familia a partir de una meta creada por el padre. "
        "Recibe `goal_id`, `member_id` (UUID), `rewards_system_type`, `rewards_system_value`, "
        "`accumulated_value`, `parent_email` y `name`. El campo `created_at` se genera automáticamente en UTC "
        "y se valida la integridad relacional con el padre, la meta base y el miembro (protegido con JWT)."
    ),
)
def create_member_goal(
    member_goal_in: MemberGoalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberGoal:
    # 1. Validar que parent_email exista y corresponda al usuario autenticado
    parent_user = db.query(User).filter(User.email_parent == member_goal_in.parent_email.lower()).first()
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

    # 2. Validar que la meta (goal_id) exista y pertenezca a esta familia
    parent_goal = (
        db.query(Goal)
        .filter(Goal.id == member_goal_in.goal_id, Goal.parent_id == current_user.id)
        .first()
    )
    if not parent_goal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontró ninguna meta creada por el padre con el `goal_id` indicado.",
        )

    # 3. Validar que el miembro (member_id UUID) exista y pertenezca a esta familia
    member_uuid_str = str(member_goal_in.member_id)
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

    member_goal = MemberGoal(
        goal_id=parent_goal.id,
        member_id=member_uuid_str,
        rewards_system_type=member_goal_in.rewards_system_type,
        rewards_system_value=member_goal_in.rewards_system_value,
        accumulated_value=member_goal_in.accumulated_value,
        parent_email=parent_user.email_parent,
        name=member_goal_in.name,
        parent_id=parent_user.id,
    )
    db.add(member_goal)
    db.commit()
    db.refresh(member_goal)
    return member_goal


@router.get(
    "",
    response_model=List[MemberGoalResponse],
    summary="Listar metas de los miembros de la familia",
    description=(
        "Obtiene todas las metas asignadas a los miembros de la familia del padre autenticado, "
        "con filtro opcional por `member_id` (UUID) o `goal_id`."
    ),
)
def list_member_goals(
    member_id: Optional[UUID] = Query(
        default=None,
        description="Filtrar opcionalmente por el UUID de un miembro específico",
    ),
    goal_id: Optional[int] = Query(
        default=None,
        description="Filtrar opcionalmente por el ID de la meta del padre",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[MemberGoal]:
    query = db.query(MemberGoal).filter(MemberGoal.parent_id == current_user.id)
    if member_id is not None:
        query = query.filter(MemberGoal.member_id == str(member_id))
    if goal_id is not None:
        query = query.filter(MemberGoal.goal_id == goal_id)
    return query.order_by(MemberGoal.created_at.desc()).all()
