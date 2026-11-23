from __future__ import annotations

import re
from typing import List, Tuple
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import ErrorCode, api_error_responses
from app.db.session import get_db
from app.models.app_version import AppVersion
from app.models.user import User
from app.schemas.app_version import (
    AppVersionCheckResponse,
    AppVersionConfigResponse,
    AppVersionConfigUpdate,
    PlatformEnum,
)

router = APIRouter()

DEFAULT_STORE_VERSIONS = {
    PlatformEnum.IOS.value: {
        "latest_version": "1.2.0",
        "min_required_version": "1.0.0",
        "force_update": False,
        "store_url": "https://apps.apple.com/app/id000000000",
        "release_notes": "Version 1.2.0 for iOS: performance improvements and security updates.",
    },
    PlatformEnum.AND.value: {
        "latest_version": "1.2.0",
        "min_required_version": "1.0.0",
        "force_update": False,
        "store_url": "https://play.google.com/store/apps/details?id=com.fhk.app",
        "release_notes": "Version 1.2.0 for Android: stability improvements and new features.",
    },
}


def _parse_version(version_str: str) -> Tuple[int, ...]:
    """Convierte una cadena de versión como '1.2.0' en una tupla numérica (1, 2, 0) para comparación."""
    numbers = re.findall(r"\d+", version_str)
    if not numbers:
        return (0,)
    return tuple(int(n) for n in numbers)


def _get_or_seed_platform_version(db: Session, platform: PlatformEnum) -> AppVersion:
    """Obtiene la configuración de versión de la plataforma en BD o crea el valor inicial por defecto."""
    record = db.query(AppVersion).filter(AppVersion.platform == platform.value).first()
    if not record:
        defaults = DEFAULT_STORE_VERSIONS[platform.value]
        record = AppVersion(
            platform=platform.value,
            latest_version=defaults["latest_version"],
            min_required_version=defaults["min_required_version"],
            force_update=defaults["force_update"],
            store_url=defaults["store_url"],
            release_notes=defaults["release_notes"],
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


@router.get(
    "/check",
    response_model=AppVersionCheckResponse,
    summary="Check whether the app has the latest store version installed",
    description=(
        "Public **GET** endpoint. You **MUST** send both `platform` and `current_version` as **Query Parameters**:\n\n"
        "| Query Parameter | Required | Allowed Values | Example |\n"
        "| :--- | :---: | :--- | :--- |\n"
        "| `platform` | **Yes** | `IOS` or `AND` | `IOS` |\n"
        "| `current_version` | **Yes** | Semantic version string (e.g. `1.0.0`) | `1.0.0` |\n\n"
        "**Example Request:**\n"
        "`GET /api/v1/app-version/check?platform=IOS&current_version=1.0.0`\n\n"
        "Compares `current_version` against the latest published store version to indicate whether the app is up to date, "
        "if an optional update is available (`update_available: true`), or if a mandatory update is required (`force_update: true`)."
    ),
)
def check_app_version(
    platform: PlatformEnum = Query(
        ...,
        description="**Required.** Target mobile platform: `IOS` (Apple App Store) or `AND` (Google Play Store).",
        examples=["IOS"],
    ),
    current_version: str = Query(
        ...,
        min_length=1,
        max_length=30,
        description="**Required.** Currently installed app version on the device (e.g. `1.0.0`).",
        examples=["1.0.0"],
    ),
    db: Session = Depends(get_db),
) -> AppVersionCheckResponse:
    store_config = _get_or_seed_platform_version(db, platform)

    current_tuple = _parse_version(current_version)
    latest_tuple = _parse_version(store_config.latest_version)
    min_required_tuple = _parse_version(store_config.min_required_version)

    is_up_to_date = current_tuple >= latest_tuple
    update_available = current_tuple < latest_tuple
    force_update = (current_tuple < min_required_tuple) or (
        store_config.force_update and update_available
    )

    if is_up_to_date:
        message = f"Your {platform.value} app is up to date ({current_version})."
    elif force_update:
        message = (
            f"Mandatory update required. Please update to version "
            f"{store_config.latest_version} to continue using the application."
        )
    else:
        message = (
            f"A new version ({store_config.latest_version}) is available in the store "
            f"for {platform.value}."
        )

    return AppVersionCheckResponse(
        platform=platform,
        current_version=current_version,
        latest_version=store_config.latest_version,
        min_required_version=store_config.min_required_version,
        is_up_to_date=is_up_to_date,
        update_available=update_available,
        force_update=force_update,
        store_url=store_config.store_url,
        release_notes=store_config.release_notes,
        message=message,
    )


@router.get(
    "",
    response_model=List[AppVersionConfigResponse],
    summary="List configured store versions (IOS and AND)",
    description="Returns the current store version configuration stored in the database for both platforms.",
)
def list_store_versions(db: Session = Depends(get_db)) -> List[AppVersion]:
    _get_or_seed_platform_version(db, PlatformEnum.IOS)
    _get_or_seed_platform_version(db, PlatformEnum.AND)
    return db.query(AppVersion).order_by(AppVersion.platform.asc()).all()


@router.put(
    "/{platform}",
    response_model=AppVersionConfigResponse,
    summary="Update the published store version for IOS or AND (JWT Protected)",
    description=(
        "Updates the database record for the latest store version (`latest_version`), "
        "minimum required version (`min_required_version`), and whether updating is mandatory (`force_update`)."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.ACCOUNT_INACTIVE),
)
def update_store_version(
    platform: PlatformEnum,
    config_in: AppVersionConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AppVersion:
    record = _get_or_seed_platform_version(db, platform)
    record.latest_version = config_in.latest_version
    record.min_required_version = config_in.min_required_version
    record.force_update = config_in.force_update
    record.store_url = config_in.store_url
    record.release_notes = config_in.release_notes

    db.add(record)
    db.commit()
    db.refresh(record)
    return record
