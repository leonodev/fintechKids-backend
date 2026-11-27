from __future__ import annotations

from typing import Any, Dict, List
from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class RemoteConfig(Base, TimestampMixin):
    """Stores remote app configuration flags, enabled languages, and bottom-bar menu items."""

    __tablename__ = "remote_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    config_key: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    cached_time_expiration: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    enabled_languages: Mapped[Dict[str, bool]] = mapped_column(JSON, nullable=False)
    menus_bottom_bar_enables: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
