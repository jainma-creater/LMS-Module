"""Database queries for enrollment and assignment."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.enrollments.models import Enrollment, EnrollmentStatus


def get_enrollment(db: Session, enrollment_id: uuid.UUID) -> Enrollment | None:
    return db.get(Enrollment, enrollment_id)


def get_active_enrollment(
    db: Session, learner_id: uuid.UUID, course_id: uuid.UUID
) -> Enrollment | None:
    stmt = select(Enrollment).where(
        Enrollment.learner_id == learner_id,
        Enrollment.course_id == course_id,
        Enrollment.status.not_in([EnrollmentStatus.COMPLETED, EnrollmentStatus.WITHDRAWN]),
    )
    return db.execute(stmt).scalar_one_or_none()


def get_latest_enrollment(
    db: Session, learner_id: uuid.UUID, course_id: uuid.UUID
) -> Enrollment | None:
    """Return the most recent enrollment for a learner/course, if any."""
    stmt = (
        select(Enrollment)
        .where(Enrollment.learner_id == learner_id, Enrollment.course_id == course_id)
        .order_by(Enrollment.assigned_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalar_one_or_none()


def list_for_learner(db: Session, learner_id: uuid.UUID) -> list[Enrollment]:
    stmt = (
        select(Enrollment)
        .where(Enrollment.learner_id == learner_id)
        .order_by(Enrollment.assigned_at.desc())
    )
    return list(db.execute(stmt).scalars())


def list_for_course(db: Session, course_id: uuid.UUID) -> list[Enrollment]:
    stmt = (
        select(Enrollment)
        .where(Enrollment.course_id == course_id)
        .order_by(Enrollment.assigned_at.desc())
    )
    return list(db.execute(stmt).scalars())
