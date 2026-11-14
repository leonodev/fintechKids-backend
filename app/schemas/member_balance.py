from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class MemberBalanceCreate(BaseModel):
    member_id: UUID = Field(
        ...,
        description="UUID del miembro de la familia (`identification_uuid` en `/api/v1/family-members`)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    coins_obtained: int = Field(
        ...,
        ge=0,
        description="Cantidad de monedas obtenidas por el miembro",
        examples=[150],
    )
    time_obtained: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tiempo obtenido por el miembro (ej. `01:30:00` o `90m`)",
        examples=["01:30:00"],
    )


class MemberBalanceUpdate(BaseModel):
    coins_obtained: Optional[int] = Field(
        default=None,
        ge=0,
        description="Nueva cantidad de monedas obtenidas por el miembro",
        examples=[200],
    )
    time_obtained: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Nuevo tiempo obtenido por el miembro",
        examples=["02:00:00"],
    )


class MemberBalanceResponse(BaseModel):
    id: int = Field(..., description="ID único del registro de balance en base de datos")
    created_at: datetime = Field(..., description="Fecha y hora de creación auto-generada por el backend en UTC")
    member_id: UUID = Field(..., description="UUID del miembro de la familia")
    coins_obtained: int = Field(..., description="Cantidad de monedas obtenidas")
    time_obtained: str = Field(..., description="Tiempo obtenido")
    parent_id: int = Field(..., description="ID de relación (Foreign Key) con la cuenta del padre en `users`")
    updated_at: datetime = Field(..., description="Última actualización en UTC")

    model_config = ConfigDict(from_attributes=True)
