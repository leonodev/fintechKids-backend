from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
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
    created_at: datetime = Field(..., description="Fecha y hora de registro auto-generada por el backend en UTC")
    name_family: str = Field(..., description="Nombre de la familia")
    email_parent: EmailStr = Field(..., description="Correo electrónico del padre/tutor")
    approve_pin: str = Field(..., description="PIN de aprobación")
    is_active: bool = Field(..., description="Indica si la cuenta está activa")
    updated_at: datetime = Field(..., description="Última actualización en UTC")

    model_config = ConfigDict(from_attributes=True)
