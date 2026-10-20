"""Business logic for enrollment and assignment.

Assignments are authorized by the ``enrollments:assign`` permission at the
router; the service validates domain preconditions (course is published, learner
exists, no duplicate active enrollment) and records audit events atomically.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditOutcome
from app.modules.courses import repository as courses_repository
from app.modules.courses.models import CourseStatus
from app.modules.enrollments import repository
from app.modules.enrollments.models import AssignmentSource, Enrollment, EnrollmentStatus
from app.modules.users import repository as users_repository
from app.security.errors import AuthorizationError
from app.security.principal import Principal


class EnrollmentNotFoundError(Exception):
    """No enrollment exists for the given identifier."""


class AlreadyEnrolledError(Exception):
    """The learner already has an active enrollment in the course."""


class CourseNotEnrollableError(Exception):
    """The course does not exist or is not published."""


class LearnerNotFoundError(Exception):
    """No learner exists for the given identifier."""


def is_overdue(enrollment: Enrollment, *, now: datetime | None = None) -> bool:
    if enrollment.due_at is None or enrollment.status in (
        EnrollmentStatus.COMPLETED,
        EnrollmentStatus.WITHDRAWN,
    ):
        return False
    reference = now or datetime.now(UTC)
    due_at = enrollment.due_at
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=UTC)
    return due_at < reference


def assign(
    db: Session,
    *,
    actor: Principal,
    course_id: uuid.UUID,
    learner_id: uuid.UUID,
    due_at: datetime | None = None,
) -> Enrollment:
    course = courses_repository.get_course(db, course_id)
    if course is None or course.status != CourseStatus.PUBLISHED:
        raise CourseNotEnrollableError(str(course_id))
    if users_repository.get_user_by_id(db, learner_id) is None:
        raise LearnerNotFoundError(str(learner_id))
    if repository.get_active_enrollment(db, learner_id, course_id) is not None:
        raise AlreadyEnrolledError(str(learner_id))

    enrollment = Enrollment(
        learner_id=learner_id,
        course_id=course_id,
        assignment_source=AssignmentSource.ADMIN,
        assigned_by=actor.user_id,
        due_at=due_at,
        status=EnrollmentStatus.ASSIGNED,
    )
    db.add(enrollment)
    db.flush()
    audit_service.record_event(
        db,
        action=audit_service.ACTION_ENROLLMENT_ASSIGNED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="enrollment",
        target_id=str(enrollment.id),
        metadata={"learner_id": str(learner_id), "course_id": str(course_id)},
    )
    db.commit()
    db.refresh(enrollment)
    return enrollment


def update_due_date(
    db: Session, *, actor: Principal, enrollment_id: uuid.UUID, due_at: datetime | None
) -> Enrollment:
    enrollment = repository.get_enrollment(db, enrollment_id)
    if enrollment is None:
        raise EnrollmentNotFoundError(str(enrollment_id))
    enrollment.due_at = due_at
    audit_service.record_event(
        db,
        action=audit_service.ACTION_ENROLLMENT_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="enrollment",
        target_id=str(enrollment.id),
        metadata={"field": "due_at"},
    )
    db.commit()
    db.refresh(enrollment)
    return enrollment


def get_enrollment(db: Session, enrollment_id: uuid.UUID) -> Enrollment:
    enrollment = repository.get_enrollment(db, enrollment_id)
    if enrollment is None:
        raise EnrollmentNotFoundError(str(enrollment_id))
    return enrollment


def get_enrollment_for(
    db: Session, *, principal: Principal, enrollment_id: uuid.UUID
) -> Enrollment:
    """Return an enrollment the principal may read.

    Owners may always read their own enrollment. Callers authorized for
    ``enrollments:assign`` may read any. Everyone else is denied.
    """
    enrollment = get_enrollment(db, enrollment_id)
    if enrollment.learner_id == principal.user_id:
        return enrollment
    if principal.has_permission("enrollments:assign"):
        return enrollment
    raise AuthorizationError()


def list_for_learner(db: Session, learner_id: uuid.UUID) -> list[Enrollment]:
    return repository.list_for_learner(db, learner_id)


def list_for_course(db: Session, course_id: uuid.UUID) -> list[Enrollment]:
    return repository.list_for_course(db, course_id)


def mark_in_progress(db: Session, enrollment: Enrollment) -> None:
    """Transition an assigned enrollment to in-progress. Does not commit."""
    if enrollment.status == EnrollmentStatus.ASSIGNED:
        enrollment.status = EnrollmentStatus.IN_PROGRESS


def mark_completed(db: Session, enrollment: Enrollment, *, when: datetime) -> None:
    """Mark an enrollment completed. Does not commit."""
    enrollment.status = EnrollmentStatus.COMPLETED
    enrollment.completed_at = when


def withdraw(db: Session, enrollment: Enrollment, *, when: datetime) -> None:
    """Remove the learner's access before completion. Progress history is kept.

    Does not commit. Completed enrollments are never withdrawn.
    """
    if enrollment.status == EnrollmentStatus.COMPLETED:
        raise ValueError("completed enrollments cannot be withdrawn")
    enrollment.status = EnrollmentStatus.WITHDRAWN
    enrollment.withdrawn_at = when


def set_due_date(enrollment: Enrollment, *, due_at: datetime | None) -> None:
    """Set the due date on an enrollment. Does not commit."""
    enrollment.due_at = due_at
