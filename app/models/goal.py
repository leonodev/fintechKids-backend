from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Goal(Base, TimestampMixin):
    """Tabla que almacena las metas (goals) configuradas por el padre/tutor de la familia."""

    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    measure_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False, index=True)
    email_parent: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    parent: Mapped["User"] = relationship("User", back_populates="goals")
