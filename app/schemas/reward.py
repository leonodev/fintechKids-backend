from __future__ import annotations

from datetime import datetime
from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class RewardCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nombre de la recompensa creada por el padre",
        examples=["1 hora de videojuegos"],
    )
    time_required: str = Field(
        ...,
        min_length=1,
        max_length=100,
        validation_alias=AliasChoices("time_required", "time_requiered"),
        description="Tiempo requerido para reclamar la recompensa (acepta `time_required` o `time_requiered`)",
        examples=["01:00:00"],
    )
    coins_required: int = Field(
        ...,
        ge=0,
        description="Cantidad de monedas requeridas para reclamar la recompensa",
        examples=[100],
    )
    email_parent: EmailStr = Field(
        ...,
        description="Correo electrónico del padre/tutor propietario de la recompensa",
        examples=["padre@fhk.app"],
    )


class RewardResponse(BaseModel):
    id: int = Field(..., description="ID único de la recompensa en base de datos")
    created_at: datetime = Field(..., description="Fecha y hora de creación auto-generada por el backend en UTC")
    name: str = Field(..., description="Nombre de la recompensa")
    time_required: str = Field(..., description="Tiempo requerido para la recompensa")
    coins_required: int = Field(..., description="Monedas requeridas para la recompensa")
    email_parent: EmailStr = Field(..., description="Correo del padre/tutor")
    parent_id: int = Field(..., description="ID de relación (Foreign Key) con la cuenta del padre en `users`")
    updated_at: datetime = Field(..., description="Última actualización en UTC")

    model_config = ConfigDict(from_attributes=True)
