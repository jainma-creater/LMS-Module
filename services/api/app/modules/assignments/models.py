"""Persistence models for course assignments.

- ``course_assignments``: one row per learner assignment to a published course.
  ``source`` is ``individual`` (assigned directly) or ``group`` (created when a
  learning-group assignment expanded to the learner or the learner joined the
  group). Cancelling sets ``status='cancelled'`` and keeps the row as history.
- ``group_course_assignments``: a course assigned to a learning group. Membership
  changes apply the active group assignments to the learners concerned.

Invariants (enforced by partial unique indexes, not only by application code):

- At most one *active* assignment per learner and course.
- At most one *active* group assignment per group and course.

``enrollment_id`` links an assignment to the enrollment (progress record) created
for the learner's linked user. It stays NULL while the learner has no account, and
the assignment is then reported as ``awaiting_account``.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppBase


class AssignmentStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class AssignmentSource(StrEnum):
    INDIVIDUAL = "individual"
    GROUP = "group"


class GroupCourseAssignment(AppBase):
    __tablename__ = "group_course_assignments"
    __table_args__ = (
        Index(
            "uq_group_course_assignments_active",
            "group_id",
            "course_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
        Index("ix_group_course_assignments_course", "course_id"),
    )

    group_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("learning_groups.id", ondelete="RESTRICT"), nullable=False
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AssignmentStatus.ACTIVE)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)


class CourseAssignment(AppBase):
    __tablename__ = "course_assignments"
    __table_args__ = (
        Index(
            "uq_course_assignments_active",
            "course_id",
            "learner_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
        Index("ix_course_assignments_learner", "learner_id"),
        Index("ix_course_assignments_group_assignment", "group_assignment_id"),
        Index("ix_course_assignments_status_due", "status", "due_at"),
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="RESTRICT"), nullable=False
    )
    learner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("learners.id", ondelete="RESTRICT"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    group_assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("group_course_assignments.id", ondelete="SET NULL"), nullable=True
    )
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=AssignmentStatus.ACTIVE)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancel_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    enrollment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("enrollments.id", ondelete="SET NULL"), nullable=True
    )
