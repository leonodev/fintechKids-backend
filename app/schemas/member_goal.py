from __future__ import annotations

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MemberGoalCreate(BaseModel):
    goal_id: int = Field(
        ...,
        description="ID de la meta creada por el padre en `/api/v1/goals`",
        examples=[1],
    )
    member_id: UUID = Field(
        ...,
        description="UUID del miembro de la familia (`identification_uuid` en `/api/v1/family-members`)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    rewards_system_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tipo de sistema de recompensa seleccionado (ej. `points`, `stars`, `coins`, `allowance`)",
        examples=["stars"],
    )
    rewards_system_value: int = Field(
        ...,
        ge=0,
        description="Valor de la recompensa asignada al completar la meta",
        examples=[10],
    )
    accumulated_value: int = Field(
        default=0,
        ge=0,
        description="Valor acumulado hasta el momento en la meta del miembro",
        examples=[0],
    )
    parent_email: EmailStr = Field(
        ...,
        description="Correo electrónico del padre/tutor registrado (misma relación que con las tablas anteriores)",
        examples=["padre@fhk.app"],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nombre de la meta para el miembro",
        examples=["Lectura diaria"],
    )


class MemberGoalResponse(BaseModel):
    id: int = Field(..., description="ID único de la meta del miembro en base de datos")
    created_at: datetime = Field(..., description="Fecha y hora de creación auto-generada por el backend en UTC")
    goal_id: int = Field(..., description="ID de la meta base creada por el padre")
    member_id: UUID = Field(..., description="UUID del miembro de la familia")
    rewards_system_type: str = Field(..., description="Tipo de sistema de recompensa")
    rewards_system_value: int = Field(..., description="Valor de la recompensa")
    accumulated_value: int = Field(..., description="Valor acumulado actual")
    parent_email: EmailStr = Field(..., description="Correo del padre/tutor")
    name: str = Field(..., description="Nombre de la meta del miembro")
    parent_id: int = Field(..., description="ID de relación (Foreign Key) con la cuenta del padre en `users`")
    updated_at: datetime = Field(..., description="Última actualización en UTC")

    model_config = ConfigDict(from_attributes=True)
