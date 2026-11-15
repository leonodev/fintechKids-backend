from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MemberRewardStateEnum(str, Enum):
    PENDING = "PENDING"
    COLLECTED = "COLLECTED"
    COLLETED = "COLLETED"


class MemberRewardCreate(BaseModel):
    member_id: UUID = Field(
        ...,
        description="UUID del miembro de la familia (`identification_uuid` en `/api/v1/family-members`)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    parent_email: EmailStr = Field(
        ...,
        description="Correo electrónico del padre/tutor registrado (misma relación que en los módulos anteriores)",
        examples=["padre@fhk.app"],
    )
    reward_id: Optional[int] = Field(
        default=None,
        description=(
            "(Recomendado) ID de la recompensa creada por el padre en `/api/v1/rewards`. "
            "Si lo envías, el backend resuelve y guarda automáticamente `name_reward` desde la base de datos."
        ),
        examples=[1],
    )
    name_reward: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description=(
            "Nombre de la recompensa. Si envías `reward_id`, este campo es opcional porque el backend "
            "lo toma automáticamente de la lista de `rewards` del padre."
        ),
        examples=["1 hora de videojuegos"],
    )
    claimed_value: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Valor reclamado por el miembro (ej. `100 coins` o `01:00:00`)",
        examples=["100 coins"],
    )
    state: MemberRewardStateEnum = Field(
        default=MemberRewardStateEnum.PENDING,
        description=(
            "Estado de la recompensa reclamada: `PENDING` (al seleccionarla el miembro) "
            "o `COLLECTED` / `COLLETED` (cuando el padre la marca como entregada/cobrada)."
        ),
        examples=["PENDING"],
    )


class MemberRewardUpdate(BaseModel):
    state: MemberRewardStateEnum = Field(
        ...,
        description="Nuevo estado de la recompensa (`PENDING`, `COLLECTED` o `COLLETED`)",
        examples=["COLLECTED"],
    )
    claimed_value: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Actualizar opcionalmente el valor reclamado",
    )


class MemberRewardResponse(BaseModel):
    id: int = Field(..., description="ID único de la recompensa reclamada en base de datos")
    created_at: datetime = Field(..., description="Fecha y hora de creación auto-generada por el backend en UTC")
    reward_id: Optional[int] = Field(default=None, description="ID de la recompensa original del padre")
    member_id: UUID = Field(..., description="UUID del miembro de la familia")
    parent_email: EmailStr = Field(..., description="Correo del padre/tutor")
    name_reward: str = Field(..., description="Nombre de la recompensa")
    claimed_value: str = Field(..., description="Valor reclamado")
    state: MemberRewardStateEnum = Field(..., description="Estado actual (`PENDING`, `COLLECTED` / `COLLETED`)")
    parent_id: int = Field(..., description="ID de relación (Foreign Key) con la cuenta del padre en `users`")
    updated_at: datetime = Field(..., description="Última actualización en UTC")

    model_config = ConfigDict(from_attributes=True)


class MemberRewardDeleteResponse(BaseModel):
    message: str = Field(
        ...,
        description="Mensaje de confirmación de eliminación",
        examples=["Recompensa reclamada eliminada correctamente."],
    )
    member_reward_id: int = Field(
        ...,
        description="ID de la recompensa reclamada que fue eliminada",
        examples=[1],
    )
