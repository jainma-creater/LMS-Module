"""Business logic for the course catalog.

Authorization decisions are made by the router via permission dependencies; the
service receives an already-resolved :class:`Principal` and only enforces
domain rules (state transitions, ordering, uniqueness) and records audit events
in the same transaction as the mutation.
"""

import re
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditOutcome
from app.modules.courses import repository
from app.modules.courses.models import Course, CourseStatus, CourseTag, Lesson, Module
from app.modules.courses.schemas import (
    CourseCreate,
    CourseUpdate,
    LessonCreate,
    LessonUpdate,
    ModuleCreate,
    ModuleUpdate,
    validate_lesson_content,
)
from app.security.principal import Principal

_SLUG_RE = re.compile(r"[^a-z0-9]+")


class CourseNotFoundError(Exception):
    """No course exists for the given identifier."""


class ModuleNotFoundError(Exception):
    """No module exists for the given identifier."""


class LessonNotFoundError(Exception):
    """No lesson exists for the given identifier."""


class CourseNotEditableError(Exception):
    """The course is archived and cannot be edited."""


class CourseAlreadyPublishedError(Exception):
    """The course is already published."""


class CourseNotPublishedError(Exception):
    """The operation requires a published course."""


class CourseNotPublishableError(Exception):
    """The course has no modules or no lessons and cannot be published."""


class InvalidReorderError(Exception):
    """The reorder payload does not match the current children exactly."""


class InvalidLessonContentError(Exception):
    """Lesson content is missing or is not a valid http(s) URL for its type."""


def slugify(title: str) -> str:
    slug = _SLUG_RE.sub("-", title.strip().lower()).strip("-")
    return slug or "course"


def _unique_slug(db: Session, title: str) -> str:
    base = slugify(title)
    candidate = base
    suffix = 2
    while repository.slug_exists(db, candidate):
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def _get_course_or_raise(db: Session, course_id: uuid.UUID) -> Course:
    course = repository.get_course(db, course_id)
    if course is None:
        raise CourseNotFoundError(str(course_id))
    return course


def _ensure_editable(course: Course) -> None:
    if course.status == CourseStatus.ARCHIVED:
        raise CourseNotEditableError(course.id)


def _touch_content(course: Course) -> None:
    """Bump the content revision when a published course is edited."""
    if course.status == CourseStatus.PUBLISHED:
        course.version += 1


def _apply_tags(course: Course, tags: list[str]) -> None:
    """Reconcile a course's tag rows with the desired (already normalized) tags."""
    desired = set(tags)
    existing = {link.tag: link for link in list(course.tag_links)}
    for tag, link in existing.items():
        if tag not in desired:
            course.tag_links.remove(link)
    for tag in tags:
        if tag not in existing:
            course.tag_links.append(CourseTag(tag=tag))


def create_course(db: Session, *, actor: Principal, data: CourseCreate) -> Course:
    course = Course(
        title=data.title,
        slug=_unique_slug(db, data.title),
        short_description=data.short_description,
        description=data.description,
        category=data.category,
        difficulty_level=data.difficulty_level.value,
        estimated_minutes=data.estimated_minutes,
        thumbnail_url=data.thumbnail_url,
        status=CourseStatus.DRAFT,
        owner_id=actor.user_id,
        is_mandatory=data.is_mandatory,
        validity_days=data.validity_days,
    )
    db.add(course)
    db.flush()
    _apply_tags(course, data.tags)
    audit_service.record_event(
        db,
        action=audit_service.ACTION_COURSE_CREATED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="course",
        target_id=str(course.id),
        metadata={"title": course.title, "slug": course.slug},
    )
    db.commit()
    db.refresh(course)
    return course


def update_course(
    db: Session, *, actor: Principal, course_id: uuid.UUID, data: CourseUpdate
) -> Course:
    course = _get_course_or_raise(db, course_id)
    _ensure_editable(course)
    provided = data.model_fields_set
    changes: dict[str, object] = {}
    for field in (
        "title",
        "short_description",
        "description",
        "category",
        "estimated_minutes",
        "thumbnail_url",
        "is_mandatory",
        "validity_days",
    ):
        if field in provided:
            value = getattr(data, field)
            if field == "title" and value is None:
                continue
            setattr(course, field, value)
            changes[field] = value
    if "difficulty_level" in provided and data.difficulty_level is not None:
        course.difficulty_level = data.difficulty_level.value
        changes["difficulty_level"] = data.difficulty_level.value
    if "tags" in provided and data.tags is not None:
        _apply_tags(course, data.tags)
        changes["tags"] = data.tags
    if changes:
        _touch_content(course)
        audit_service.record_event(
            db,
            action=audit_service.ACTION_COURSE_UPDATED,
            outcome=AuditOutcome.SUCCESS,
            actor_id=actor.user_id,
            target_type="course",
            target_id=str(course.id),
            metadata={"fields": sorted(changes)},
        )
        db.commit()
    db.refresh(course)
    return course


def publish_course(db: Session, *, actor: Principal, course_id: uuid.UUID) -> Course:
    course = _get_course_or_raise(db, course_id)
    if course.status == CourseStatus.PUBLISHED:
        raise CourseAlreadyPublishedError(str(course_id))
    if course.status == CourseStatus.ARCHIVED:
        raise CourseNotPublishableError("archived courses cannot be published")
    if repository.count_modules(db, course_id) == 0 or repository.count_lessons(db, course_id) == 0:
        raise CourseNotPublishableError(
            "a course needs at least one module and one lesson before publishing"
        )
    course.status = CourseStatus.PUBLISHED
    course.published_at = datetime.now(UTC)
    audit_service.record_event(
        db,
        action=audit_service.ACTION_COURSE_PUBLISHED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="course",
        target_id=str(course.id),
        metadata={"version": course.version},
    )
    db.commit()
    db.refresh(course)
    return course


def archive_course(db: Session, *, actor: Principal, course_id: uuid.UUID) -> Course:
    course = _get_course_or_raise(db, course_id)
    course.status = CourseStatus.ARCHIVED
    audit_service.record_event(
        db,
        action=audit_service.ACTION_COURSE_ARCHIVED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="course",
        target_id=str(course.id),
    )
    db.commit()
    db.refresh(course)
    return course


def get_course(db: Session, course_id: uuid.UUID) -> Course:
    return _get_course_or_raise(db, course_id)


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
    return repository.list_catalog(
        db,
        search=search,
        category=category,
        difficulty_level=difficulty_level,
        tag=tag,
        limit=limit,
        offset=offset,
    )


def list_course_categories(db: Session) -> list[str]:
    return repository.list_categories(db)


def get_published_course_by_slug(db: Session, slug: str) -> Course | None:
    """Return a published course by slug, or ``None`` for drafts, archived, or unknown."""
    course = repository.get_course_by_slug(db, slug)
    if course is None or course.status != CourseStatus.PUBLISHED:
        return None
    return course


def list_all_courses(
    db: Session,
    *,
    status: str | None = None,
    category: str | None = None,
    difficulty_level: str | None = None,
) -> list[Course]:
    return repository.list_courses(
        db,
        status=status,
        category=category,
        difficulty_level=difficulty_level,
    )


def course_counts(db: Session, course_id: uuid.UUID) -> tuple[int, int]:
    return repository.count_modules(db, course_id), repository.count_lessons(db, course_id)


def create_module(
    db: Session, *, actor: Principal, course_id: uuid.UUID, data: ModuleCreate
) -> Module:
    course = _get_course_or_raise(db, course_id)
    _ensure_editable(course)
    module = Module(
        course_id=course_id,
        title=data.title,
        description=data.description,
        sort_order=repository.next_module_order(db, course_id),
    )
    db.add(module)
    db.flush()
    _touch_content(course)
    audit_service.record_event(
        db,
        action=audit_service.ACTION_MODULE_CREATED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="module",
        target_id=str(module.id),
        metadata={"course_id": str(course_id)},
    )
    db.commit()
    db.refresh(module)
    return module


def update_module(
    db: Session, *, actor: Principal, module_id: uuid.UUID, data: ModuleUpdate
) -> Module:
    module = repository.get_module(db, module_id)
    if module is None:
        raise ModuleNotFoundError(str(module_id))
    course = _get_course_or_raise(db, module.course_id)
    _ensure_editable(course)
    changes: dict[str, object] = {}
    for field in ("title", "description"):
        value = getattr(data, field)
        if value is not None:
            setattr(module, field, value)
            changes[field] = value
    if changes:
        _touch_content(course)
        audit_service.record_event(
            db,
            action=audit_service.ACTION_MODULE_UPDATED,
            outcome=AuditOutcome.SUCCESS,
            actor_id=actor.user_id,
            target_type="module",
            target_id=str(module.id),
            metadata={"fields": sorted(changes)},
        )
        db.commit()
    db.refresh(module)
    return module


def delete_module(db: Session, *, actor: Principal, module_id: uuid.UUID) -> None:
    module = repository.get_module(db, module_id)
    if module is None:
        raise ModuleNotFoundError(str(module_id))
    course = _get_course_or_raise(db, module.course_id)
    _ensure_editable(course)
    for lesson in repository.list_lessons(db, module_id):
        db.delete(lesson)
    db.delete(module)
    _touch_content(course)
    audit_service.record_event(
        db,
        action=audit_service.ACTION_MODULE_DELETED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="module",
        target_id=str(module.id),
        metadata={"course_id": str(course.id)},
    )
    db.commit()


def reorder_modules(
    db: Session, *, actor: Principal, course_id: uuid.UUID, ordered_ids: list[uuid.UUID]
) -> list[Module]:
    course = _get_course_or_raise(db, course_id)
    _ensure_editable(course)
    modules = repository.list_modules(db, course_id)
    existing = {module.id for module in modules}
    if existing != set(ordered_ids) or len(ordered_ids) != len(existing):
        raise InvalidReorderError("ordered_ids must contain each module exactly once")
    by_id = {module.id: module for module in modules}
    for index, module_id in enumerate(ordered_ids):
        by_id[module_id].sort_order = index
    _touch_content(course)
    audit_service.record_event(
        db,
        action=audit_service.ACTION_MODULE_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="course",
        target_id=str(course_id),
        metadata={"reordered_modules": len(ordered_ids)},
    )
    db.commit()
    return repository.list_modules(db, course_id)


def create_lesson(
    db: Session, *, actor: Principal, module_id: uuid.UUID, data: LessonCreate
) -> Lesson:
    module = repository.get_module(db, module_id)
    if module is None:
        raise ModuleNotFoundError(str(module_id))
    course = _get_course_or_raise(db, module.course_id)
    _ensure_editable(course)
    lesson = Lesson(
        module_id=module_id,
        title=data.title,
        description=data.description,
        content_type=data.content_type.value,
        content=data.content,
        estimated_minutes=data.estimated_minutes,
        is_required=data.is_required,
        sort_order=repository.next_lesson_order(db, module_id),
    )
    db.add(lesson)
    db.flush()
    _touch_content(course)
    audit_service.record_event(
        db,
        action=audit_service.ACTION_LESSON_CREATED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="lesson",
        target_id=str(lesson.id),
        metadata={"module_id": str(module_id)},
    )
    db.commit()
    db.refresh(lesson)
    return lesson


def update_lesson(
    db: Session, *, actor: Principal, lesson_id: uuid.UUID, data: LessonUpdate
) -> Lesson:
    lesson = repository.get_lesson(db, lesson_id)
    if lesson is None:
        raise LessonNotFoundError(str(lesson_id))
    module = repository.get_module(db, lesson.module_id)
    course = _get_course_or_raise(db, module.course_id)
    _ensure_editable(course)
    provided = data.model_fields_set
    effective_type = (
        data.content_type.value if data.content_type is not None else lesson.content_type
    )
    effective_content = data.content if "content" in provided else lesson.content
    try:
        normalised_content = validate_lesson_content(effective_type, effective_content)
    except ValueError as exc:
        raise InvalidLessonContentError(str(exc)) from None
    changes: dict[str, object] = {}
    for field in ("title", "description", "content", "estimated_minutes", "is_required"):
        if field in provided:
            value = getattr(data, field)
            if field == "title" and value is None:
                continue
            setattr(lesson, field, value)
            changes[field] = value
    if "content_type" in provided and data.content_type is not None:
        lesson.content_type = data.content_type.value
        changes["content_type"] = data.content_type.value
    if lesson.content != normalised_content:
        lesson.content = normalised_content
        changes["content"] = normalised_content
    if changes:
        _touch_content(course)
        audit_service.record_event(
            db,
            action=audit_service.ACTION_LESSON_UPDATED,
            outcome=AuditOutcome.SUCCESS,
            actor_id=actor.user_id,
            target_type="lesson",
            target_id=str(lesson.id),
            metadata={"fields": sorted(changes)},
        )
        db.commit()
    db.refresh(lesson)
    return lesson


def delete_lesson(db: Session, *, actor: Principal, lesson_id: uuid.UUID) -> None:
    lesson = repository.get_lesson(db, lesson_id)
    if lesson is None:
        raise LessonNotFoundError(str(lesson_id))
    module = repository.get_module(db, lesson.module_id)
    course = _get_course_or_raise(db, module.course_id)
    _ensure_editable(course)
    db.delete(lesson)
    _touch_content(course)
    audit_service.record_event(
        db,
        action=audit_service.ACTION_LESSON_DELETED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="lesson",
        target_id=str(lesson_id),
        metadata={"module_id": str(module.id)},
    )
    db.commit()


def reorder_lessons(
    db: Session, *, actor: Principal, module_id: uuid.UUID, ordered_ids: list[uuid.UUID]
) -> list[Lesson]:
    module = repository.get_module(db, module_id)
    if module is None:
        raise ModuleNotFoundError(str(module_id))
    course = _get_course_or_raise(db, module.course_id)
    _ensure_editable(course)
    lessons = repository.list_lessons(db, module_id)
    existing = {lesson.id for lesson in lessons}
    if existing != set(ordered_ids) or len(ordered_ids) != len(existing):
        raise InvalidReorderError("ordered_ids must contain each lesson exactly once")
    by_id = {lesson.id: lesson for lesson in lessons}
    for index, lesson_id in enumerate(ordered_ids):
        by_id[lesson_id].sort_order = index
    _touch_content(course)
    audit_service.record_event(
        db,
        action=audit_service.ACTION_LESSON_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="module",
        target_id=str(module_id),
        metadata={"reordered_lessons": len(ordered_ids)},
    )
    db.commit()
    return repository.list_lessons(db, module_id)


def get_course_content(
    db: Session, course_id: uuid.UUID
) -> tuple[Course, list[tuple[Module, list[Lesson]]]]:
    course = _get_course_or_raise(db, course_id)
    # One query for all modules, one for all their lessons (no per-module query).
    lessons_by_module = repository.list_lessons_for_course(db, course_id)
    tree: list[tuple[Module, list[Lesson]]] = [
        (module, lessons_by_module.get(module.id, []))
        for module in repository.list_modules(db, course_id)
    ]
    return course, tree
