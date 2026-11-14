from __future__ import annotations

from typing import List, TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.member_goal import MemberGoal
    from app.models.user import User


class FamilyMember(Base, TimestampMixin):
    """Tabla que almacena los miembros de una familia vinculados al padre/tutor."""

    __tablename__ = "family_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    identification_uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    email_parent: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    name_family: Mapped[str] = mapped_column(String(255), nullable=False)
    member_name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_name: Mapped[str] = mapped_column(String(255), nullable=False)
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    parent: Mapped["User"] = relationship("User", back_populates="family_members")
    member_goals: Mapped[List["MemberGoal"]] = relationship(
        "MemberGoal",
        back_populates="member",
        cascade="all, delete-orphan",
    )
