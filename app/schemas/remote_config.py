from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class MenuHomeItemSchema(BaseModel):
    id: int = Field(
        ...,
        ge=1,
        description="Unique numeric identifier for the bottom-bar menu item",
        examples=[1],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Internal identifier name for the menu tab (e.g. `payments`)",
        examples=["payments"],
    )
    icon: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Icon asset identifier used by the mobile client",
        examples=["payments-icon"],
    )
    label_localized_key: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Localization key used by the app to display the tab title",
        examples=["key_payments_title"],
    )
    active: bool = Field(
        default=True,
        description="Controls whether this bottom-bar menu item is enabled in the app",
        examples=[True],
    )


def _normalize_enabled_languages(value: Dict[str, bool]) -> Dict[str, bool]:
    normalized: Dict[str, bool] = {}
    for raw_key, enabled in value.items():
        clean_key = raw_key.strip().lower()
        if not clean_key:
            raise ValueError("Language codes in enabled_languages cannot be empty.")
        normalized[clean_key] = bool(enabled)
    return normalized


def _validate_unique_menu_ids(items: List[MenuHomeItemSchema]) -> List[MenuHomeItemSchema]:
    seen_ids = set()
    for item in items:
        if item.id in seen_ids:
            raise ValueError(f"Duplicate menu item id detected in menus_bottom_bar_enables: {item.id}")
        seen_ids.add(item.id)
    return items


class RemoteConfigResponse(BaseModel):
    cached_time_expiration: int = Field(
        ...,
        ge=0,
        description="Client-side remote config cache duration in minutes",
        examples=[5],
    )
    enabled_languages: Dict[str, bool] = Field(
        ...,
        description="Map of ISO language codes to boolean flags so languages can be toggled without deleting them",
        examples=[{"es": True, "fr": True, "en": True, "it": True}],
    )
    menus_bottom_bar_enables: List[MenuHomeItemSchema] = Field(
        ...,
        description="List of bottom-bar home menu items and their active flags",
        examples=[
            [
                {
                    "name": "payments",
                    "id": 1,
                    "icon": "payments-icon",
                    "label_localized_key": "key_payments_title",
                    "active": True,
                }
            ]
        ],
    )
    updated_at: datetime = Field(
        ...,
        description="UTC timestamp of the last remote configuration update",
    )

    model_config = ConfigDict(from_attributes=True)


class RemoteConfigUpdate(BaseModel):
    cached_time_expiration: Optional[int] = Field(
        default=None,
        ge=0,
        le=1440,
        description="Client-side remote config cache duration in minutes (0 to 1440)",
        examples=[5],
    )
    enabled_languages: Optional[Dict[str, bool]] = Field(
        default=None,
        description="Map of ISO language codes to boolean flags (e.g. `{\"es\": true, \"fr\": false}`)",
        examples=[{"es": True, "fr": True, "en": True, "it": True}],
    )
    menus_bottom_bar_enables: Optional[List[MenuHomeItemSchema]] = Field(
        default=None,
        description="Updated list of bottom-bar menu items and their visibility/active status",
        examples=[
            [
                {
                    "name": "payments",
                    "id": 1,
                    "icon": "payments-icon",
                    "label_localized_key": "key_payments_title",
                    "active": True,
                }
            ]
        ],
    )

    @field_validator("enabled_languages")
    @classmethod
    def validate_languages(cls, value: Optional[Dict[str, bool]]) -> Optional[Dict[str, bool]]:
        if value is None:
            return None
        return _normalize_enabled_languages(value)

    @field_validator("menus_bottom_bar_enables")
    @classmethod
    def validate_menu_items(
        cls, value: Optional[List[MenuHomeItemSchema]]
    ) -> Optional[List[MenuHomeItemSchema]]:
        if value is None:
            return None
        return _validate_unique_menu_ids(value)
