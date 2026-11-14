from __future__ import annotations

from typing import Optional
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AppVersion(Base, TimestampMixin):
    """Tabla que almacena la versión actual publicada en tiendas (App Store / Google Play)."""

    __tablename__ = "app_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    platform: Mapped[str] = mapped_column(String(10), unique=True, index=True, nullable=False)  # "IOS" o "AND"
    latest_version: Mapped[str] = mapped_column(String(30), nullable=False)
    min_required_version: Mapped[str] = mapped_column(String(30), nullable=False)
    force_update: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    store_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    release_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
