from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.activity_log import ActivityLog
from app.models.user import User
from app.schemas.activity_log import ActivityLogResponse

router = APIRouter()


@router.get(
    "",
    response_model=List[ActivityLogResponse],
    summary="Consultar el historial de actividad (Audit Log) de la familia",
    description=(
        "Devuelve la bitácora histórica de acciones registradas automáticamente en el backend "
        "para la familia del padre autenticado, ordenada de la más reciente a la más antigua. "
        "Permite filtrar opcionalmente por `member_id`, `entity_type` o `action` (protegido con JWT)."
    ),
)
def list_activity_logs(
    member_id: Optional[str] = Query(
        default=None,
        description="Filtrar opcionalmente por el UUID de un miembro de la familia",
    ),
    entity_type: Optional[str] = Query(
        default=None,
        description="Filtrar por módulo/entidad (`users`, `family_members`, `goals`, `member_goals`, `member_balances`, `rewards`, `member_rewards`, `tasks`)",
    ),
    action: Optional[str] = Query(
        default=None,
        description="Filtrar por tipo de acción (ej. `CREATE_TASK`, `UPDATE_BALANCE`, `CLAIM_REWARD`)",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Cantidad máxima de eventos históricos a devolver",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ActivityLog]:
    query = db.query(ActivityLog).filter(ActivityLog.parent_id == current_user.id)
    if member_id:
        query = query.filter(ActivityLog.member_id == member_id)
    if entity_type:
        query = query.filter(ActivityLog.entity_type == entity_type)
    if action:
        query = query.filter(ActivityLog.action == action)

    return query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.desc()).limit(limit).all()
