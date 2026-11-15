from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TaskStatusEnum(str, Enum):
    ENABLE = "enable"
    DISABLE = "disable"


class TaskCreate(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Nombre de la tarea creada por el padre",
        examples=["Ordenar la habitación"],
    )
    time_granted: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tiempo otorgado como recompensa al completar la tarea",
        examples=["00:30:00"],
    )
    coins_granted: int = Field(
        ...,
        ge=0,
        description="Cantidad de monedas otorgadas al completar la tarea",
        examples=[50],
    )
    email_parent: EmailStr = Field(
        ...,
        description="Correo electrónico del padre/tutor propietario de la tarea",
        examples=["padre@fhk.app"],
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Descripción detallada de la tarea a realizar",
        examples=["Tender la cama y guardar los juguetes antes de cenar."],
    )
    status: TaskStatusEnum = Field(
        default=TaskStatusEnum.ENABLE,
        description="Estado inicial de la tarea (`enable` o `disable`). Por defecto se asigna `enable` automáticamente.",
        examples=["enable"],
    )


class TaskUpdate(BaseModel):
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Nuevo nombre de la tarea",
        examples=["Ordenar habitación y escritorio"],
    )
    time_granted: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Nuevo tiempo otorgado",
        examples=["00:45:00"],
    )
    coins_granted: Optional[int] = Field(
        default=None,
        ge=0,
        description="Nueva cantidad de monedas otorgadas",
        examples=[75],
    )
    description: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Nueva descripción de la tarea",
        examples=["Tender la cama, guardar juguetes y limpiar el escritorio."],
    )
    status: Optional[TaskStatusEnum] = Field(
        default=None,
        description="Nuevo estado de la tarea (`enable` para habilitarla o `disable` para deshabilitarla)",
        examples=["disable"],
    )


class TaskResponse(BaseModel):
    id: int = Field(..., description="ID único de la tarea en base de datos")
    created_at: datetime = Field(..., description="Fecha y hora de creación auto-generada por el backend en UTC")
    name: str = Field(..., description="Nombre de la tarea")
    time_granted: str = Field(..., description="Tiempo otorgado")
    coins_granted: int = Field(..., description="Monedas otorgadas")
    email_parent: EmailStr = Field(..., description="Correo del padre/tutor")
    description: str = Field(..., description="Descripción de la tarea")
    status: TaskStatusEnum = Field(..., description="Estado actual de la tarea (`enable` o `disable`)")
    parent_id: int = Field(..., description="ID de relación (Foreign Key) con la cuenta del padre en `users`")
    updated_at: datetime = Field(..., description="Última actualización en UTC")

    model_config = ConfigDict(from_attributes=True)


class TaskDeleteResponse(BaseModel):
    message: str = Field(
        ...,
        description="Mensaje de confirmación de eliminación",
        examples=["Tarea eliminada correctamente."],
    )
    task_id: int = Field(..., description="ID de la tarea eliminada", examples=[1])
