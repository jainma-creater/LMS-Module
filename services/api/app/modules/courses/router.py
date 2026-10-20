"""HTTP endpoints for course authoring and the learner catalog.

Authorization is enforced by permission dependencies. Route handlers only
translate domain errors to HTTP responses and shape responses; all state and
audit logic lives in the service layer.

Draft courses are invisible to callers without ``courses:write``: reads of a
non-published course return 404 rather than 403 so the catalog does not leak
unpublished content.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.courses import service
from app.modules.courses.models import Course, CourseStatus, Lesson
from app.modules.courses.schemas import (
    CourseContentResponse,
    CourseCounts,
    CourseCreate,
    CourseDetailResponse,
    CoursePage,
    CourseResponse,
    CourseStatusView,
    CourseUpdate,
    LessonCreate,
    LessonResponse,
    LessonUpdate,
    ModuleCreate,
    ModuleResponse,
    ModuleUpdate,
    ModuleWithLessonsResponse,
    ReorderRequest,
)
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.security.principal import Principal

router = APIRouter(tags=["courses"])
admin_router = APIRouter(prefix="/admin", tags=["courses-admin"])

_DOMAIN_ERRORS = (
    service.CourseNotFoundError,
    service.ModuleNotFoundError,
    service.LessonNotFoundError,
    service.CourseNotEditableError,
    service.CourseAlreadyPublishedError,
    service.CourseNotPublishableError,
    service.InvalidReorderError,
    service.InvalidLessonContentError,
)


def _to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, service.CourseNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    if isinstance(exc, service.ModuleNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found.")
    if isinstance(exc, service.LessonNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found.")
    if isinstance(exc, service.CourseNotEditableError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Archived courses cannot be edited."
        )
    if isinstance(exc, service.CourseAlreadyPublishedError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Course is already published."
        )
    if isinstance(exc, service.CourseNotPublishableError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, service.InvalidReorderError):
        return HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ordering must list each item exactly once.",
        )
    if isinstance(exc, service.InvalidLessonContentError):
        return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected.")


def _can_see_draft(principal: Principal) -> bool:
    return principal.has_permission(Permission.COURSES_WRITE.value)


def _cache_private(response: Response, seconds: int) -> None:
    """Allow short browser caching without letting shared proxies cache it.

    Catalog reads are permission-gated, so responses must never be stored by a
    shared cache: ``private`` keeps the content out of intermediary caches while
    still letting the caller's browser reuse it briefly.
    """
    response.headers["Cache-Control"] = f"private, max-age={seconds}"


def _detail(db: Session, course: Course) -> CourseDetailResponse:
    modules, lessons = service.course_counts(db, course.id)
    return CourseDetailResponse(
        **CourseResponse.model_validate(course).model_dump(),
        counts=CourseCounts(modules=modules, lessons=lessons),
    )


# --------------------------------------------------------------------------- #
# Learner catalog (any authenticated principal with courses:read)
# --------------------------------------------------------------------------- #
@router.get("/courses", response_model=CoursePage)
def list_catalog(
    response: Response,
    search: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=100),
    difficulty_level: str | None = Query(default=None, max_length=20),
    tag: str | None = Query(default=None, max_length=50),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_permission(Permission.COURSES_READ)),
    db: Session = Depends(get_db),
) -> CoursePage:
    courses, total = service.list_catalog(
        db,
        search=search,
        category=category,
        difficulty_level=difficulty_level,
        tag=tag,
        limit=limit,
        offset=offset,
    )
    _cache_private(response, 30)
    return CoursePage(
        items=[CourseStatusView.model_validate(course) for course in courses],
        total=total,
        limit=limit,
        offset=offset,
    )


# Declared before ``/courses/{course_id}`` so the literal segments are not
# captured as a (invalid) UUID path parameter.
@router.get("/courses/categories", response_model=list[str])
def list_course_categories(
    response: Response,
    principal: Principal = Depends(require_permission(Permission.COURSES_READ)),
    db: Session = Depends(get_db),
) -> list[str]:
    _cache_private(response, 300)
    return service.list_course_categories(db)


@router.get("/courses/slug/{slug}", response_model=CourseDetailResponse)
def get_course_by_slug(
    slug: str,
    response: Response,
    principal: Principal = Depends(require_permission(Permission.COURSES_READ)),
    db: Session = Depends(get_db),
) -> CourseDetailResponse:
    course = service.get_published_course_by_slug(db, slug)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    _cache_private(response, 60)
    return _detail(db, course)


@router.get("/courses/{course_id}", response_model=CourseDetailResponse)
def get_course(
    course_id: uuid.UUID,
    response: Response,
    principal: Principal = Depends(require_permission(Permission.COURSES_READ)),
    db: Session = Depends(get_db),
) -> CourseDetailResponse:
    try:
        course = service.get_course(db, course_id)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    if course.status != CourseStatus.PUBLISHED and not _can_see_draft(principal):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    _cache_private(response, 60)
    return _detail(db, course)


@router.get("/courses/{course_id}/content", response_model=CourseContentResponse)
def get_course_content(
    course_id: uuid.UUID,
    response: Response,
    principal: Principal = Depends(require_permission(Permission.COURSES_READ)),
    db: Session = Depends(get_db),
) -> CourseContentResponse:
    try:
        course, tree = service.get_course_content(db, course_id)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    if course.status != CourseStatus.PUBLISHED and not _can_see_draft(principal):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    _cache_private(response, 60)
    modules = [
        ModuleWithLessonsResponse(
            **ModuleResponse.model_validate(module).model_dump(),
            lessons=[LessonResponse.model_validate(lesson) for lesson in lessons],
        )
        for module, lessons in tree
    ]
    return CourseContentResponse(course=CourseResponse.model_validate(course), modules=modules)


# --------------------------------------------------------------------------- #
# Course authoring (courses:write)
# --------------------------------------------------------------------------- #
@admin_router.get("/courses", response_model=list[CourseResponse])
def list_all_courses(
    status_filter: CourseStatus | None = Query(default=None, alias="status"),
    category: str | None = Query(default=None, max_length=100),
    difficulty_level: str | None = Query(default=None, max_length=20),
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> list[CourseResponse]:
    courses = service.list_all_courses(
        db,
        status=status_filter.value if status_filter else None,
        category=category,
        difficulty_level=difficulty_level,
    )
    return [CourseResponse.model_validate(course) for course in courses]


@router.post("/courses", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    payload: CourseCreate,
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> CourseResponse:
    try:
        course = service.create_course(db, actor=principal, data=payload)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return CourseResponse.model_validate(course)


@router.patch("/courses/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: uuid.UUID,
    payload: CourseUpdate,
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> CourseResponse:
    try:
        course = service.update_course(db, actor=principal, course_id=course_id, data=payload)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return CourseResponse.model_validate(course)


@router.post("/courses/{course_id}/publish", response_model=CourseResponse)
def publish_course(
    course_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.COURSES_PUBLISH)),
    db: Session = Depends(get_db),
) -> CourseResponse:
    try:
        course = service.publish_course(db, actor=principal, course_id=course_id)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return CourseResponse.model_validate(course)


@router.post("/courses/{course_id}/archive", response_model=CourseResponse)
def archive_course(
    course_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.COURSES_PUBLISH)),
    db: Session = Depends(get_db),
) -> CourseResponse:
    try:
        course = service.archive_course(db, actor=principal, course_id=course_id)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return CourseResponse.model_validate(course)


# --------------------------------------------------------------------------- #
# Modules and lessons (courses:write)
# --------------------------------------------------------------------------- #
@router.post(
    "/courses/{course_id}/modules",
    response_model=ModuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_module(
    course_id: uuid.UUID,
    payload: ModuleCreate,
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> ModuleResponse:
    try:
        module = service.create_module(db, actor=principal, course_id=course_id, data=payload)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return ModuleResponse.model_validate(module)


@router.put("/courses/{course_id}/modules/order", response_model=list[ModuleResponse])
def reorder_modules(
    course_id: uuid.UUID,
    payload: ReorderRequest,
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> list[ModuleResponse]:
    try:
        modules = service.reorder_modules(
            db, actor=principal, course_id=course_id, ordered_ids=payload.ordered_ids
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return [ModuleResponse.model_validate(module) for module in modules]


@router.patch("/modules/{module_id}", response_model=ModuleResponse)
def update_module(
    module_id: uuid.UUID,
    payload: ModuleUpdate,
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> ModuleResponse:
    try:
        module = service.update_module(db, actor=principal, module_id=module_id, data=payload)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return ModuleResponse.model_validate(module)


@router.delete("/modules/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_module(
    module_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> None:
    try:
        service.delete_module(db, actor=principal, module_id=module_id)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None


@router.post(
    "/modules/{module_id}/lessons",
    response_model=LessonResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_lesson(
    module_id: uuid.UUID,
    payload: LessonCreate,
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> LessonResponse:
    try:
        lesson = service.create_lesson(db, actor=principal, module_id=module_id, data=payload)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return LessonResponse.model_validate(lesson)


@router.put("/modules/{module_id}/lessons/order", response_model=list[LessonResponse])
def reorder_lessons(
    module_id: uuid.UUID,
    payload: ReorderRequest,
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> list[LessonResponse]:
    try:
        lessons: list[Lesson] = service.reorder_lessons(
            db, actor=principal, module_id=module_id, ordered_ids=payload.ordered_ids
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return [LessonResponse.model_validate(lesson) for lesson in lessons]


@router.patch("/lessons/{lesson_id}", response_model=LessonResponse)
def update_lesson(
    lesson_id: uuid.UUID,
    payload: LessonUpdate,
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> LessonResponse:
    try:
        lesson = service.update_lesson(db, actor=principal, lesson_id=lesson_id, data=payload)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return LessonResponse.model_validate(lesson)


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.COURSES_WRITE)),
    db: Session = Depends(get_db),
) -> None:
    try:
        service.delete_lesson(db, actor=principal, lesson_id=lesson_id)
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
