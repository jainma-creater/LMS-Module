"""Persistence model for course enrollment / assignment.

An enrollment ties a learner to a course. History is preserved: completed
enrollments remain as rows, and a partial unique index guarantees at most one
*active* (not completed) enrollment per learner and course. "Overdue" is derived
from ``due_at`` and status rather than stored, so it can never drift from the
dates.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppBase


class EnrollmentStatus(StrEnum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    # Access was removed (assignment cancelled or group membership removed) before
    # completion. Progress rows are kept as history; the learner may be re-assigned.
    WITHDRAWN = "withdrawn"


class AssignmentSource(StrEnum):
    SELF = "self"
    ADMIN = "admin"
    MANAGER = "manager"
    GROUP = "group"
    SYSTEM = "system"


class Enrollment(AppBase):
    __tablename__ = "enrollments"
    __table_args__ = (
        Index("ix_enrollments_learner_status", "learner_id", "status"),
        Index("ix_enrollments_course_status", "course_id", "status"),
        Index("ix_enrollments_due_at", "due_at"),
        Index(
            "uq_enrollments_active",
            "learner_id",
            "course_id",
            unique=True,
            postgresql_where=text("status NOT IN ('completed', 'withdrawn')"),
            sqlite_where=text("status NOT IN ('completed', 'withdrawn')"),
        ),
    )

    learner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    assignment_source: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AssignmentSource.ADMIN
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EnrollmentStatus.ASSIGNED
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
