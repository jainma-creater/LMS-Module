"""Business logic for lesson progress and course completion.

Completion is computed server-side and never trusts a client-supplied flag. A
completion is recorded once per learner/course and retains the rule version used,
so historical evidence stays interpretable if the rule changes.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditOutcome
from app.modules.courses import repository as courses_repository
from app.modules.enrollments import repository as enrollments_repository
from app.modules.enrollments import service as enrollments_service
from app.modules.enrollments.models import EnrollmentStatus
from app.modules.progress import repository
from app.modules.progress.models import (
    CourseCompletion,
    LessonProgress,
    LessonProgressStatus,
)

COMPLETION_RULE_VERSION = 1


class LessonNotFoundError(Exception):
    """No lesson exists for the given identifier."""


class CourseNotFoundError(Exception):
    """No course exists for the given identifier."""


class NotEnrolledError(Exception):
    """The learner has no enrollment in the lesson's course."""


def _now() -> datetime:
    return datetime.now(UTC)


def _evaluate_completion(
    db: Session, *, user_id: uuid.UUID, course_id: uuid.UUID, now: datetime
) -> None:
    total = repository.count_required_lessons(db, course_id)
    if total == 0:
        return
    completed = repository.count_completed_required(db, user_id, course_id)
    if completed < total:
        return

    enrollment = enrollments_repository.get_latest_enrollment(db, user_id, course_id)
    if repository.get_completion(db, user_id, course_id) is None:
        db.add(
            CourseCompletion(
                user_id=user_id,
                course_id=course_id,
                completed_at=now,
                completion_rule_version=COMPLETION_RULE_VERSION,
            )
        )
        audit_service.record_event(
            db,
            action=audit_service.ACTION_COURSE_COMPLETED,
            outcome=AuditOutcome.SUCCESS,
            actor_id=user_id,
            target_type="course",
            target_id=str(course_id),
            metadata={"rule_version": COMPLETION_RULE_VERSION},
        )
    if enrollment is not None and enrollment.status != EnrollmentStatus.COMPLETED:
        enrollments_service.mark_completed(db, enrollment, when=now)


def record_progress(
    db: Session,
    *,
    user_id: uuid.UUID,
    lesson_id: uuid.UUID,
    status: str,
    last_position: int | None,
) -> LessonProgress:
    lesson = courses_repository.get_lesson(db, lesson_id)
    if lesson is None:
        raise LessonNotFoundError(str(lesson_id))
    module = courses_repository.get_module(db, lesson.module_id)
    course_id = module.course_id

    enrollment = enrollments_repository.get_latest_enrollment(db, user_id, course_id)
    if enrollment is None or enrollment.status == EnrollmentStatus.WITHDRAWN:
        raise NotEnrolledError(str(course_id))

    now = _now()
    progress = repository.get_progress(db, user_id, lesson_id)
    if progress is None:
        progress = LessonProgress(user_id=user_id, lesson_id=lesson_id, status=status)
        db.add(progress)
    progress.status = status
    progress.last_position = last_position
    if status == LessonProgressStatus.COMPLETED:
        progress.completed_at = now
    else:
        progress.completed_at = None

    if enrollment.status != EnrollmentStatus.COMPLETED:
        enrollments_service.mark_in_progress(db, enrollment)

    db.flush()
    _evaluate_completion(db, user_id=user_id, course_id=course_id, now=now)
    db.commit()
    db.refresh(progress)
    return progress


def progress_summary(
    db: Session, *, user_id: uuid.UUID, course_id: uuid.UUID
) -> tuple[int, int, int, bool]:
    total = repository.count_required_lessons(db, course_id)
    completed = repository.count_completed_required(db, user_id, course_id)
    if total == 0:
        return 0, 0, 0, False
    percent = min(100, round(completed / total * 100))
    return total, completed, percent, completed >= total


def progress_summaries(
    db: Session, *, user_id: uuid.UUID, course_ids: list[uuid.UUID]
) -> dict[uuid.UUID, tuple[int, int, int, bool]]:
    """Batch variant of :func:`progress_summary` for list endpoints.

    Uses two grouped queries regardless of how many courses are requested, so
    a learner with many enrollments does not trigger a query per course.
    """
    if not course_ids:
        return {}
    required = repository.required_counts_for_courses(db, course_ids)
    completed = repository.completed_counts_for_courses(db, user_id, course_ids)
    summaries: dict[uuid.UUID, tuple[int, int, int, bool]] = {}
    for course_id in course_ids:
        total = required.get(course_id, 0)
        done = completed.get(course_id, 0)
        if total == 0:
            summaries[course_id] = (0, 0, 0, False)
            continue
        percent = min(100, round(done / total * 100))
        summaries[course_id] = (total, done, percent, done >= total)
    return summaries


def course_progress(
    db: Session, *, user_id: uuid.UUID, course_id: uuid.UUID
) -> tuple[int, int, int, bool, list[LessonProgress]]:
    if courses_repository.get_course(db, course_id) is None:
        raise CourseNotFoundError(str(course_id))
    total, completed, percent, is_complete = progress_summary(
        db, user_id=user_id, course_id=course_id
    )
    rows = repository.list_progress_for_course(db, user_id, course_id)
    return total, completed, percent, is_complete, rows


def list_completions(db: Session, user_id: uuid.UUID) -> list[CourseCompletion]:
    return repository.list_completions(db, user_id)
