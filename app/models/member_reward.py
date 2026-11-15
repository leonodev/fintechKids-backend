from __future__ import annotations

from typing import Optional, TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.family_member import FamilyMember
    from app.models.reward import Reward
    from app.models.user import User


class MemberReward(Base, TimestampMixin):
    """Tabla que almacena las recompensas reclamadas/cobradas por un miembro de la familia."""

    __tablename__ = "member_rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    reward_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("rewards.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    member_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("family_members.identification_uuid"),
        nullable=False,
        index=True,
    )
    parent_email: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    name_reward: Mapped[str] = mapped_column(String(255), nullable=False)
    claimed_value: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False, index=True)
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    parent: Mapped["User"] = relationship("User", back_populates="member_rewards")
    member: Mapped["FamilyMember"] = relationship("FamilyMember", back_populates="member_rewards")
    reward: Mapped[Optional["Reward"]] = relationship("Reward", back_populates="member_rewards")
