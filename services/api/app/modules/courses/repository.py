"""Database queries for the course catalog."""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.courses.models import Course, CourseStatus, CourseTag, Lesson, Module


def get_course(db: Session, course_id: uuid.UUID) -> Course | None:
    return db.get(Course, course_id)


def get_courses_by_ids(db: Session, course_ids: list[uuid.UUID]) -> dict[uuid.UUID, Course]:
    """Fetch many courses in one round trip, keyed by id.

    Avoids the per-row lookups that turn list endpoints into N+1 queries.
    """
    if not course_ids:
        return {}
    stmt = select(Course).where(Course.id.in_(course_ids))
    return {course.id: course for course in db.execute(stmt).unique().scalars()}


def get_course_by_slug(db: Session, slug: str) -> Course | None:
    return db.execute(select(Course).where(Course.slug == slug)).scalar_one_or_none()


def slug_exists(db: Session, slug: str) -> bool:
    return db.execute(select(Course.id).where(Course.slug == slug)).scalar_one_or_none() is not None


def list_courses(
    db: Session,
    *,
    status: str | None = None,
    category: str | None = None,
    difficulty_level: str | None = None,
) -> list[Course]:
    """List courses for authoring, newest first, with deterministic tie-break."""
    stmt = select(Course)
    conditions: list = []
    if status is not None:
        conditions.append(Course.status == status)
    if category is not None:
        conditions.append(Course.category == category)
    if difficulty_level is not None:
        conditions.append(Course.difficulty_level == difficulty_level)
    if conditions:
        stmt = stmt.where(*conditions)
    stmt = stmt.order_by(Course.created_at.desc(), Course.id.desc())
    return list(db.execute(stmt).scalars())


def _catalog_conditions(
    *,
    search: str | None,
    category: str | None,
    difficulty_level: str | None,
) -> list:
    conditions: list = [Course.status == CourseStatus.PUBLISHED.value]
    if category is not None:
        conditions.append(Course.category == category)
    if difficulty_level is not None:
        conditions.append(Course.difficulty_level == difficulty_level)
    if search is not None and search.strip():
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                Course.title.ilike(pattern),
                Course.short_description.ilike(pattern),
                Course.description.ilike(pattern),
            )
        )
    return conditions


def list_catalog(
    db: Session,
    *,
    search: str | None = None,
    category: str | None = None,
    difficulty_level: str | None = None,
    tag: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[Course], int]:
    """Return a page of published courses and the total for the same filters.

    Ordering is deterministic (``created_at`` then ``id``, both descending) so
    pagination is stable across requests.
    """
    conditions = _catalog_conditions(
        search=search, category=category, difficulty_level=difficulty_level
    )
    stmt = select(Course)
    count_stmt = select(func.count(func.distinct(Course.id)))
    if tag is not None:
        stmt = stmt.join(CourseTag, CourseTag.course_id == Course.id)
        count_stmt = count_stmt.join(CourseTag, CourseTag.course_id == Course.id)
        conditions.append(CourseTag.tag == tag)
    stmt = stmt.where(*conditions).order_by(Course.created_at.desc(), Course.id.desc())
    count_stmt = count_stmt.where(*conditions)
    total = int(db.execute(count_stmt).scalar_one())
    if limit is not None:
        stmt = stmt.limit(limit).offset(offset)
    return list(db.execute(stmt).unique().scalars()), total


def list_categories(db: Session) -> list[str]:
    """Distinct categories among published courses, sorted for stable output."""
    stmt = (
        select(Course.category)
        .where(Course.status == CourseStatus.PUBLISHED.value, Course.category.is_not(None))
        .distinct()
        .order_by(Course.category)
    )
    return [category for category in db.execute(stmt).scalars() if category]


def list_modules(db: Session, course_id: uuid.UUID) -> list[Module]:
    stmt = (
        select(Module).where(Module.course_id == course_id).order_by(Module.sort_order, Module.id)
    )
    return list(db.execute(stmt).scalars())


def get_module(db: Session, module_id: uuid.UUID) -> Module | None:
    return db.get(Module, module_id)


def list_lessons(db: Session, module_id: uuid.UUID) -> list[Lesson]:
    stmt = (
        select(Lesson).where(Lesson.module_id == module_id).order_by(Lesson.sort_order, Lesson.id)
    )
    return list(db.execute(stmt).scalars())


def list_lessons_for_course(
    db: Session, course_id: uuid.UUID
) -> dict[uuid.UUID, list[Lesson]]:
    """Lessons for every module in a course, grouped by module, in one query.

    Returns a dict keyed by module id; modules without lessons are absent.
    Callers should default missing keys to an empty list.
    """
    stmt = (
        select(Lesson, Module.id)
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.course_id == course_id)
        .order_by(Lesson.sort_order, Lesson.id)
    )
    grouped: dict[uuid.UUID, list[Lesson]] = {}
    for lesson, module_id in db.execute(stmt):
        grouped.setdefault(module_id, []).append(lesson)
    return grouped


def get_lesson(db: Session, lesson_id: uuid.UUID) -> Lesson | None:
    return db.get(Lesson, lesson_id)


def next_module_order(db: Session, course_id: uuid.UUID) -> int:
    stmt = select(func.coalesce(func.max(Module.sort_order), -1)).where(
        Module.course_id == course_id
    )
    return int(db.execute(stmt).scalar_one()) + 1


def next_lesson_order(db: Session, module_id: uuid.UUID) -> int:
    stmt = select(func.coalesce(func.max(Lesson.sort_order), -1)).where(
        Lesson.module_id == module_id
    )
    return int(db.execute(stmt).scalar_one()) + 1


def count_modules(db: Session, course_id: uuid.UUID) -> int:
    stmt = select(func.count()).select_from(Module).where(Module.course_id == course_id)
    return int(db.execute(stmt).scalar_one())


def count_lessons(db: Session, course_id: uuid.UUID) -> int:
    stmt = (
        select(func.count())
        .select_from(Lesson)
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.course_id == course_id)
    )
    return int(db.execute(stmt).scalar_one())


def required_lesson_ids(db: Session, course_id: uuid.UUID) -> list[uuid.UUID]:
    stmt = (
        select(Lesson.id)
        .join(Module, Module.id == Lesson.module_id)
        .where(Module.course_id == course_id, Lesson.is_required.is_(True))
    )
    return list(db.execute(stmt).scalars())
