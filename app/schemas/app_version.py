from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class PlatformEnum(str, Enum):
    IOS = "IOS"
    AND = "AND"


class AppVersionCheckResponse(BaseModel):
    platform: PlatformEnum = Field(
        ...,
        description="Plataforma consultada (`IOS` para Apple App Store, `AND` para Google Play Store)",
        examples=["IOS"],
    )
    current_version: str = Field(
        ...,
        description="Versión instalada actualmente en el dispositivo del usuario",
        examples=["1.0.0"],
    )
    latest_version: str = Field(
        ...,
        description="Última versión disponible en la tienda correspondiente",
        examples=["1.2.0"],
    )
    min_required_version: str = Field(
        ...,
        description="Versión mínima permitida para seguir usando la app sin actualizar",
        examples=["1.0.0"],
    )
    is_up_to_date: bool = Field(
        ...,
        description="`true` si la app ya tiene instalada la última versión (o superior) de la tienda",
        examples=[False],
    )
    update_available: bool = Field(
        ...,
        description="`true` si existe una versión más reciente publicada en la tienda",
        examples=[True],
    )
    force_update: bool = Field(
        ...,
        description="`true` si la actualización es obligatoria (bloqueante) para continuar usando la app",
        examples=[False],
    )
    store_url: Optional[str] = Field(
        default=None,
        description="Enlace directo a la tienda (App Store / Google Play) para descargar la actualización",
        examples=["https://apps.apple.com/app/id000000000"],
    )
    release_notes: Optional[str] = Field(
        default=None,
        description="Notas de la versión con las novedades disponibles en tienda",
        examples=["Mejoras de rendimiento y nuevas funcionalidades de seguridad."],
    )
    message: str = Field(
        ...,
        description="Mensaje descriptivo listo para mostrar al usuario o registrar en logs",
        examples=["Hay una nueva versión (1.2.0) disponible en la tienda."],
    )


class AppVersionConfigUpdate(BaseModel):
    latest_version: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Última versión publicada en la tienda (formato semántico ej. 1.2.0)",
        examples=["1.3.0"],
    )
    min_required_version: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Versión mínima obligatoria (clientes con versión menor verán force_update=true)",
        examples=["1.1.0"],
    )
    force_update: bool = Field(
        default=False,
        description="Si es `true`, fuerza la actualización a todos los usuarios que no estén en `latest_version`",
    )
    store_url: Optional[str] = Field(
        default=None,
        description="URL oficial de la app en App Store o Google Play",
        examples=["https://apps.apple.com/app/id000000000"],
    )
    release_notes: Optional[str] = Field(
        default=None,
        description="Notas de lanzamiento de la versión actual",
        examples=["Corrección de errores y mejoras de estabilidad."],
    )


class AppVersionConfigResponse(BaseModel):
    id: int
    platform: PlatformEnum
    latest_version: str
    min_required_version: str
    force_update: bool
    store_url: Optional[str] = None
    release_notes: Optional[str] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
