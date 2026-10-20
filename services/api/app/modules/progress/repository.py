"""Database queries for learning progress and completion."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.courses.models import Lesson, Module
from app.modules.progress.models import CourseCompletion, LessonProgress, LessonProgressStatus


def get_progress(db: Session, user_id: uuid.UUID, lesson_id: uuid.UUID) -> LessonProgress | None:
    stmt = select(LessonProgress).where(
        LessonProgress.user_id == user_id, LessonProgress.lesson_id == lesson_id
    )
    return db.execute(stmt).scalar_one_or_none()


def list_progress_for_course(
    db: Session, user_id: uuid.UUID, course_id: uuid.UUID
) -> list[LessonProgress]:
    stmt = (
        select(LessonProgress)
        .join(Lesson, Lesson.id == LessonProgress.lesson_id)
        .join(Module, Module.id == Lesson.module_id)
        .where(LessonProgress.user_id == user_id, Module.course_id == course_id)
    )
    return list(db.execute(stmt).scalars())


def count_required_lessons(db: Session, course_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(Lesson)
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.course_id == course_id, Lesson.is_required.is_(True))
    )
    return int(db.execute(stmt).scalar_one())


def count_completed_required(db: Session, user_id: uuid.UUID, course_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(LessonProgress)
        .join(Lesson, Lesson.id == LessonProgress.lesson_id)
        .join(Module, Module.id == Lesson.module_id)
        .where(
            LessonProgress.user_id == user_id,
            Module.course_id == course_id,
            Lesson.is_required.is_(True),
            LessonProgress.status == LessonProgressStatus.COMPLETED,
        )
    )
    return int(db.execute(stmt).scalar_one())


def required_counts_for_courses(
    db: Session, course_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Required-lesson counts for many courses in a single grouped query."""
    if not course_ids:
        return {}
    stmt = (
        select(Module.course_id, func.count(Lesson.id))
        .select_from(Lesson)
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.course_id.in_(course_ids), Lesson.is_required.is_(True))
        .group_by(Module.course_id)
    )
    return {row[0]: int(row[1]) for row in db.execute(stmt)}


def completed_counts_for_courses(
    db: Session, user_id: uuid.UUID, course_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Completed-required-lesson counts per course for a learner in one query."""
    if not course_ids:
        return {}
    stmt = (
        select(Module.course_id, func.count(LessonProgress.id))
        .select_from(LessonProgress)
        .join(Lesson, Lesson.id == LessonProgress.lesson_id)
        .join(Module, Module.id == Lesson.module_id)
        .where(
            LessonProgress.user_id == user_id,
            Module.course_id.in_(course_ids),
            Lesson.is_required.is_(True),
            LessonProgress.status == LessonProgressStatus.COMPLETED,
        )
        .group_by(Module.course_id)
    )
    return {row[0]: int(row[1]) for row in db.execute(stmt)}


def get_completion(
    db: Session, user_id: uuid.UUID, course_id: uuid.UUID
) -> CourseCompletion | None:
    stmt = select(CourseCompletion).where(
        CourseCompletion.user_id == user_id, CourseCompletion.course_id == course_id
    )
    return db.execute(stmt).scalar_one_or_none()


def list_completions(db: Session, user_id: uuid.UUID) -> list[CourseCompletion]:
    stmt = (
        select(CourseCompletion)
        .where(CourseCompletion.user_id == user_id)
        .order_by(CourseCompletion.completed_at.desc())
    )
    return list(db.execute(stmt).scalars())
