from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class Task(Base, TimestampMixin):
    """Tabla que almacena las tareas (tasks) creadas por el padre/tutor para su familia."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    time_granted: Mapped[str] = mapped_column(String(100), nullable=False)
    coins_granted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    email_parent: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="enable", nullable=False, index=True)
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    parent: Mapped["User"] = relationship("User", back_populates="tasks")
