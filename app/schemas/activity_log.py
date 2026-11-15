from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ActivityLogResponse(BaseModel):
    id: int = Field(..., description="ID único del registro de auditoría en base de datos")
    created_at: datetime = Field(..., description="Fecha y hora exacta del evento en UTC")
    parent_id: int = Field(..., description="ID de la familia/padre")
    email_parent: EmailStr = Field(..., description="Correo del padre/tutor")
    member_id: Optional[str] = Field(
        default=None,
        description="UUID del miembro de la familia involucrado en la acción (si aplica)",
    )
    action: str = Field(
        ...,
        description="Acción ejecutada (ej. `REGISTER_FAMILY`, `CREATE_MEMBER`, `UPDATE_BALANCE`, `CLAIM_REWARD`, `COLLECT_REWARD`, `CREATE_TASK`)",
        examples=["UPDATE_BALANCE"],
    )
    entity_type: str = Field(
        ...,
        description="Tabla o entidad afectada (`users`, `family_members`, `goals`, `member_goals`, `member_balances`, `rewards`, `member_rewards`, `tasks`)",
        examples=["member_balances"],
    )
    entity_id: str = Field(
        ...,
        description="ID o UUID del registro afectado",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    details: Optional[str] = Field(
        default=None,
        description="Detalle descriptivo de los cambios realizados",
        examples=["Balance actualizado: coins_obtained=220, time_obtained=02:15:00"],
    )

    model_config = ConfigDict(from_attributes=True)
