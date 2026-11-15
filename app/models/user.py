from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.activity_log import ActivityLog
    from app.models.family_member import FamilyMember
    from app.models.goal import Goal
    from app.models.member_balance import MemberBalance
    from app.models.member_goal import MemberGoal
    from app.models.member_reward import MemberReward
    from app.models.reward import Reward
    from app.models.task import Task


class User(Base):
    """Modelo de Registro de Familia / Padre en la base de datos."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    name_family: Mapped[str] = mapped_column(String(255), nullable=False)
    email_parent: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    approve_pin: Mapped[str] = mapped_column(String(50), nullable=False)
    reset_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    reset_code_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="parent", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relación con Miembros de la Familia (1 Padre/Familia -> N Miembros)
    family_members: Mapped[List["FamilyMember"]] = relationship(
        "FamilyMember",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    # Relación con Metas / Goals (1 Padre/Familia -> N Metas)
    goals: Mapped[List["Goal"]] = relationship(
        "Goal",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    # Relación con Metas de los Miembros (1 Padre/Familia -> N Metas de Miembros)
    member_goals: Mapped[List["MemberGoal"]] = relationship(
        "MemberGoal",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    # Relación con Balances de los Miembros (1 Padre/Familia -> N Balances)
    member_balances: Mapped[List["MemberBalance"]] = relationship(
        "MemberBalance",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    # Relación con Recompensas / Rewards (1 Padre/Familia -> N Recompensas)
    rewards: Mapped[List["Reward"]] = relationship(
        "Reward",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    # Relación con Recompensas reclamadas por Miembros (1 Padre/Familia -> N MemberRewards)
    member_rewards: Mapped[List["MemberReward"]] = relationship(
        "MemberReward",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    # Relación con Tareas / Tasks de la Familia (1 Padre/Familia -> N Tasks)
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    # Relación con Historial de Actividad / Auditoría (1 Padre/Familia -> N ActivityLogs)
    activity_logs: Mapped[List["ActivityLog"]] = relationship(
        "ActivityLog",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
