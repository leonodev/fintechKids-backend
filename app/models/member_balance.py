from __future__ import annotations

from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.family_member import FamilyMember
    from app.models.user import User


class MemberBalance(Base, TimestampMixin):
    """Tabla que almacena el balance de monedas y tiempo obtenido por cada miembro de la familia."""

    __tablename__ = "member_balances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    member_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("family_members.identification_uuid"),
        nullable=False,
        index=True,
    )
    coins_obtained: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    time_obtained: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    parent: Mapped["User"] = relationship("User", back_populates="member_balances")
    member: Mapped["FamilyMember"] = relationship("FamilyMember", back_populates="member_balances")
