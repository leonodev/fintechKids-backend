from __future__ import annotations

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Título del elemento",
        examples=["Suscripción Premium"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Descripción detallada del elemento",
        examples=["Acceso completo a todos los servicios desde la app móvil"],
    )
    price: float = Field(
        default=0.0,
        ge=0.0,
        description="Precio o valor numérico asociado",
        examples=[19.99],
    )
    is_completed: bool = Field(
        default=False,
        description="Estado de completado del elemento",
    )


class ItemUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0.0)
    is_completed: Optional[bool] = None


class ItemResponse(BaseModel):
    id: int = Field(..., description="ID único del elemento")
    title: str
    description: Optional[str] = None
    price: float
    is_completed: bool
    owner_id: int = Field(..., description="ID del usuario propietario")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
