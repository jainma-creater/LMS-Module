"""Persistence models for learner records and learning groups.

A learner record describes an employee who can be assigned training. It is not an
authentication identity. ``user_id`` is an optional, unique link to a
:class:`app.modules.users.models.User` (the identity used for login). Learners can
exist before they have an account, and a future identity integration can set the
link without a schema change.

Group membership keeps history: removing a member sets ``removed_at`` instead of
deleting the row, and a partial unique index allows only one *active* membership
per group and learner.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppBase


class LearnerStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class GroupStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class Learner(AppBase):
    __tablename__ = "learners"
    __table_args__ = (
        UniqueConstraint("employee_id", name="uq_learners_employee_id"),
        UniqueConstraint("email", name="uq_learners_email"),
        UniqueConstraint("user_id", name="uq_learners_user_id"),
        Index("ix_learners_status", "status"),
        Index("ix_learners_department", "department"),
    )

    employee_id: Mapped[str] = mapped_column(String(64), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    business_unit: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=LearnerStatus.ACTIVE)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class LearningGroup(AppBase):
    __tablename__ = "learning_groups"
    __table_args__ = (
        UniqueConstraint("name", name="uq_learning_groups_name"),
        Index("ix_learning_groups_status", "status"),
    )

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Free-form organizational label ("department", "team", ...). Not an enum, so the
    # application does not hard-code company structure.
    kind: Mapped[str] = mapped_column(String(50), nullable=False, default="team")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=GroupStatus.ACTIVE)


class LearningGroupMember(AppBase):
    __tablename__ = "learning_group_members"
    __table_args__ = (
        Index(
            "uq_group_members_active",
            "group_id",
            "learner_id",
            unique=True,
            postgresql_where=text("removed_at IS NULL"),
            sqlite_where=text("removed_at IS NULL"),
        ),
        Index("ix_group_members_learner", "learner_id"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("learning_groups.id", ondelete="RESTRICT"), nullable=False
    )
    learner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("learners.id", ondelete="RESTRICT"), nullable=False
    )
    added_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    removed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
