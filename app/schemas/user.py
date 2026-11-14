from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr = Field(
        ...,
        description="Correo electrónico único del usuario",
        examples=["usuario@fhk.app"],
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Nombre completo del usuario",
        examples=["Fredy León"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Contraseña (mínimo 8 caracteres)",
        examples=["MiPasswordSeguro123!"],
    )


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=150,
        description="Nuevo nombre completo del usuario",
    )
    password: Optional[str] = Field(
        default=None,
        min_length=8,
        max_length=128,
        description="Nueva contraseña (opcional)",
    )


class UserResponse(BaseModel):
    id: int = Field(..., description="ID único del usuario")
    email: EmailStr = Field(..., description="Correo electrónico del usuario")
    full_name: str = Field(..., description="Nombre completo")
    is_active: bool = Field(..., description="Indica si la cuenta está activa")
    role: str = Field(..., description="Rol del usuario (user, admin)")
    created_at: datetime = Field(..., description="Fecha de registro en UTC")
    updated_at: datetime = Field(..., description="Última actualización en UTC")

    model_config = ConfigDict(from_attributes=True)
