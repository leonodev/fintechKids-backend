from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    created_at: datetime = Field(
        ...,
        description="Timestamp de creación en hora UTC (ej. `2026-11-14T18:00:00Z`)",
        examples=["2026-11-14T18:00:00Z"],
    )
    name_family: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nombre de la familia",
        examples=["Familia León"],
    )
    email_parent: EmailStr = Field(
        ...,
        description="Correo electrónico del padre/madre o tutor",
        examples=["padre@fhk.app"],
    )
    approve_pin: str = Field(
        ...,
        min_length=4,
        max_length=50,
        description="PIN de aprobación del padre/madre",
        examples=["1234"],
    )

    @field_validator("created_at", mode="after")
    @classmethod
    def ensure_utc(cls, value: datetime) -> datetime:
        """Garantiza que el timestamp quede normalizado en zona horaria UTC."""
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class UserUpdate(BaseModel):
    name_family: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Nuevo nombre de la familia",
    )
    approve_pin: Optional[str] = Field(
        default=None,
        min_length=4,
        max_length=50,
        description="Nuevo PIN de aprobación",
    )


class UserResponse(BaseModel):
    id: int = Field(..., description="ID único del registro en base de datos")
    created_at: datetime = Field(..., description="Fecha y hora de registro en UTC")
    name_family: str = Field(..., description="Nombre de la familia")
    email_parent: EmailStr = Field(..., description="Correo electrónico del padre/tutor")
    approve_pin: str = Field(..., description="PIN de aprobación")
    is_active: bool = Field(..., description="Indica si la cuenta está activa")
    updated_at: datetime = Field(..., description="Última actualización en UTC")

    model_config = ConfigDict(from_attributes=True)
