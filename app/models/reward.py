from __future__ import annotations

from typing import List, TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.member_reward import MemberReward
    from app.models.user import User


class Reward(Base, TimestampMixin):
    """Tabla que almacena las recompensas (rewards) creadas por el padre/tutor de la familia."""

    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    time_required: Mapped[str] = mapped_column(String(100), nullable=False)
    coins_required: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    email_parent: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    parent_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    parent: Mapped["User"] = relationship("User", back_populates="rewards")
    member_rewards: Mapped[List["MemberReward"]] = relationship(
        "MemberReward",
        back_populates="reward",
    )
