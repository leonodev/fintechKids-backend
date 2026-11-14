from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.family_member import FamilyMember
    from app.models.goal import Goal
    from app.models.user import User


class MemberGoal(Base, TimestampMixin):
    """Tabla que almacena las metas asignadas/seleccionadas por un miembro de la familia."""

    __tablename__ = "member_goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    goal_id: Mapped[int] = mapped_column(Integer, ForeignKey("goals.id"), nullable=False, index=True)
    member_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("family_members.identification_uuid"),
        nullable=False,
        index=True,
    )
    rewards_system_type: Mapped[str] = mapped_column(String(100), nullable=False)
    rewards_system_value: Mapped[int] = mapped_column(Integer, nullable=False)
    accumulated_value: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parent_email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    parent: Mapped["User"] = relationship("User", back_populates="member_goals")
    goal: Mapped["Goal"] = relationship("Goal", back_populates="member_goals")
    member: Mapped["FamilyMember"] = relationship("FamilyMember", back_populates="member_goals")
