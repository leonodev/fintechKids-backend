from __future__ import annotations

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class GoalStatusEnum(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class GoalCreate(BaseModel):
    measure_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tipo de medida de la meta (ej. `minutes`, `hours`, `points`, `tasks`)",
        examples=["minutes"],
    )
    status: GoalStatusEnum = Field(
        default=GoalStatusEnum.ACTIVE,
        description="Estado de la meta (`active` o `inactive`)",
        examples=["active"],
    )
    email_parent: EmailStr = Field(
        ...,
        description="Correo electrónico del padre/tutor propietario de la meta",
        examples=["padre@fhk.app"],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nombre descriptivo de la meta",
        examples=["Lectura diaria"],
    )
    value: int = Field(
        ...,
        ge=0,
        description="Valor numérico objetivo de la meta",
        examples=[30],
    )


class GoalResponse(BaseModel):
    id: int = Field(..., description="ID único de la meta en base de datos")
    created_at: datetime = Field(..., description="Fecha y hora de creación auto-generada por el backend en UTC")
    measure_type: str = Field(..., description="Tipo de medida de la meta")
    status: GoalStatusEnum = Field(..., description="Estado actual de la meta (`active` o `inactive`)")
    email_parent: EmailStr = Field(..., description="Correo del padre/tutor")
    name: str = Field(..., description="Nombre de la meta")
    value: int = Field(..., description="Valor numérico de la meta")
    parent_id: int = Field(..., description="ID de relación (Foreign Key) con la cuenta del padre en `users`")
    updated_at: datetime = Field(..., description="Última actualización en UTC")

    model_config = ConfigDict(from_attributes=True)
