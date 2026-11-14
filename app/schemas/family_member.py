from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class FamilyMemberCreate(BaseModel):
    email_parent: EmailStr = Field(
        ...,
        description="Correo electrónico del padre/tutor registrado al que pertenece el miembro",
        examples=["padre@fhk.app"],
    )
    identification_uuid: UUID = Field(
        ...,
        description="Identificador único UUID del miembro de la familia generado desde la app",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    member_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nombre del miembro de la familia",
        examples=["Mateo"],
    )
    avatar_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nombre o identificador del avatar seleccionado en la app",
        examples=["avatar_lion_01"],
    )
    name_family: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nombre de la familia (mismo `name_family` del registro / `users/me`)",
        examples=["Familia León"],
    )


class FamilyMemberUpdate(BaseModel):
    member_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Nuevo nombre del miembro de la familia",
        examples=["Mateo León"],
    )
    avatar_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Nuevo nombre o identificador del avatar",
        examples=["avatar_tiger_02"],
    )


class FamilyMemberResponse(BaseModel):
    id: int = Field(..., description="ID numérico interno del miembro en base de datos")
    identification_uuid: UUID = Field(..., description="UUID único de identificación del miembro")
    email_parent: EmailStr = Field(..., description="Correo del padre/tutor")
    name_family: str = Field(..., description="Nombre de la familia")
    member_name: str = Field(..., description="Nombre del miembro")
    avatar_name: str = Field(..., description="Avatar asignado")
    parent_id: int = Field(..., description="ID de relación (Foreign Key) con la cuenta del padre en `users`")
    created_at: datetime = Field(..., description="Fecha de creación en UTC")
    updated_at: datetime = Field(..., description="Última actualización en UTC")

    model_config = ConfigDict(from_attributes=True)


class FamilyMemberDeleteResponse(BaseModel):
    message: str = Field(
        ...,
        description="Mensaje de confirmación de eliminación",
        examples=["Miembro de la familia eliminado correctamente."],
    )
    identification_uuid: UUID = Field(
        ...,
        description="UUID del miembro que fue eliminado",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
