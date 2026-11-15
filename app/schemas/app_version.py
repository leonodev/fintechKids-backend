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
        description="Queried platform (`IOS` for Apple App Store, `AND` for Google Play Store)",
        examples=["IOS"],
    )
    current_version: str = Field(
        ...,
        description="App version currently installed on the user's device",
        examples=["1.0.0"],
    )
    latest_version: str = Field(
        ...,
        description="Latest version available in the corresponding store",
        examples=["1.2.0"],
    )
    min_required_version: str = Field(
        ...,
        description="Minimum required version allowed to continue using the app without updating",
        examples=["1.0.0"],
    )
    is_up_to_date: bool = Field(
        ...,
        description="`true` if the app already has the latest (or newer) store version installed",
        examples=[False],
    )
    update_available: bool = Field(
        ...,
        description="`true` if a newer version is published in the store",
        examples=[True],
    )
    force_update: bool = Field(
        ...,
        description="`true` if updating is mandatory (blocking) to continue using the app",
        examples=[False],
    )
    store_url: Optional[str] = Field(
        default=None,
        description="Direct link to the store (App Store / Google Play) to download the update",
        examples=["https://apps.apple.com/app/id000000000"],
    )
    release_notes: Optional[str] = Field(
        default=None,
        description="Release notes describing what is new in the store version",
        examples=["Performance improvements and new security features."],
    )
    message: str = Field(
        ...,
        description="Descriptive status message ready to display to the user or log",
        examples=["A new version (1.2.0) is available in the store."],
    )


class AppVersionConfigUpdate(BaseModel):
    latest_version: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Latest version published in the store (semantic format, e.g. `1.2.0`)",
        examples=["1.3.0"],
    )
    min_required_version: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Minimum required version (clients below this version will receive `force_update=true`)",
        examples=["1.1.0"],
    )
    force_update: bool = Field(
        default=False,
        description="If `true`, forces an update for all users not on `latest_version`",
    )
    store_url: Optional[str] = Field(
        default=None,
        description="Official App Store or Google Play URL",
        examples=["https://apps.apple.com/app/id000000000"],
    )
    release_notes: Optional[str] = Field(
        default=None,
        description="Release notes for the current version",
        examples=["Bug fixes and stability improvements."],
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
