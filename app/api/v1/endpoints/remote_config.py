from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import ErrorCode, api_error_responses
from app.db.session import get_db
from app.models.remote_config import RemoteConfig
from app.models.user import User
from app.schemas.remote_config import RemoteConfigResponse, RemoteConfigUpdate

router = APIRouter()

DEFAULT_CONFIG_KEY = "default"
DEFAULT_CACHED_TIME_EXPIRATION = 5
DEFAULT_ENABLED_LANGUAGES: Dict[str, bool] = {
    "es": True,
    "fr": True,
    "en": True,
    "it": True,
}
DEFAULT_MENUS_BOTTOM_BAR: List[Dict[str, Any]] = [
    {
        "name": "payments",
        "id": 1,
        "icon": "payments-icon",
        "label_localized_key": "key_payments_title",
        "active": True,
    }
]


def _get_or_seed_remote_config(db: Session) -> RemoteConfig:
    """Return the active remote config record or seed default values on first access."""
    record = db.query(RemoteConfig).filter(RemoteConfig.config_key == DEFAULT_CONFIG_KEY).first()
    if not record:
        record = RemoteConfig(
            config_key=DEFAULT_CONFIG_KEY,
            cached_time_expiration=DEFAULT_CACHED_TIME_EXPIRATION,
            enabled_languages=dict(DEFAULT_ENABLED_LANGUAGES),
            menus_bottom_bar_enables=[dict(item) for item in DEFAULT_MENUS_BOTTOM_BAR],
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


@router.get(
    "",
    response_model=RemoteConfigResponse,
    summary="Get remote app configuration (languages, bottom-bar menus, and cache TTL)",
    description=(
        "Public **GET** endpoint replacing Firebase Remote Config for the mobile client.\n\n"
        "Returns:\n"
        "- `cached_time_expiration`: Cache duration in minutes.\n"
        "- `enabled_languages`: Map of language codes to booleans (`{\"es\": true, \"fr\": true, ...}`) "
        "so individual languages can be toggled off without removing them.\n"
        "- `menus_bottom_bar_enables`: List of bottom-bar menu item configurations (`id`, `name`, `icon`, "
        "`label_localized_key`, `active`)."
    ),
)
def get_remote_config(db: Session = Depends(get_db)) -> RemoteConfig:
    return _get_or_seed_remote_config(db)


@router.put(
    "",
    response_model=RemoteConfigResponse,
    summary="Update remote app configuration (JWT Protected)",
    description=(
        "Updates `cached_time_expiration`, `enabled_languages`, and/or `menus_bottom_bar_enables` "
        "in the database for the current environment. Any omitted (`null`) field keeps its existing value."
    ),
    responses=api_error_responses(ErrorCode.INVALID_OR_EXPIRED_TOKEN, ErrorCode.ACCOUNT_INACTIVE),
)
def update_remote_config(
    config_in: RemoteConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RemoteConfig:
    record = _get_or_seed_remote_config(db)

    if config_in.cached_time_expiration is not None:
        record.cached_time_expiration = config_in.cached_time_expiration
    if config_in.enabled_languages is not None:
        record.enabled_languages = config_in.enabled_languages
    if config_in.menus_bottom_bar_enables is not None:
        record.menus_bottom_bar_enables = [
            item.model_dump() for item in config_in.menus_bottom_bar_enables
        ]

    db.add(record)
    db.commit()
    db.refresh(record)
    return record
