"""HTTP endpoints for learner progress and course completion.

Learners read and write only their own progress. The learner identity always
comes from the authenticated principal, never from the request body.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.courses import repository as courses_repository
from app.modules.progress import service
from app.modules.progress.schemas import (
    CompletionItem,
    CourseProgressResponse,
    LessonProgressResponse,
    LessonProgressUpdate,
)
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.security.principal import Principal

router = APIRouter(tags=["progress"])

_DOMAIN_ERRORS = (
    service.LessonNotFoundError,
    service.CourseNotFoundError,
    service.NotEnrolledError,
)


def _to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, (service.LessonNotFoundError, service.CourseNotFoundError)):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found.")
    if isinstance(exc, service.NotEnrolledError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Not enrolled in this course."
        )
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected.")


@router.put("/lessons/{lesson_id}/progress", response_model=LessonProgressResponse)
def record_lesson_progress(
    lesson_id: uuid.UUID,
    payload: LessonProgressUpdate,
    principal: Principal = Depends(require_permission(Permission.PROGRESS_WRITE)),
    db: Session = Depends(get_db),
) -> LessonProgressResponse:
    try:
        progress = service.record_progress(
            db,
            user_id=principal.user_id,
            lesson_id=lesson_id,
            status=payload.status.value,
            last_position=payload.last_position,
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return LessonProgressResponse.model_validate(progress)


@router.get("/courses/{course_id}/progress", response_model=CourseProgressResponse)
def get_course_progress(
    course_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.LEARNING_READ)),
    db: Session = Depends(get_db),
) -> CourseProgressResponse:
    try:
        total, completed, percent, is_complete, rows = service.course_progress(
            db, user_id=principal.user_id, course_id=course_id
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return CourseProgressResponse(
        course_id=course_id,
        required_lessons=total,
        completed_lessons=completed,
        percent=percent,
        is_complete=is_complete,
        lessons=[LessonProgressResponse.model_validate(row) for row in rows],
    )


@router.get("/me/progress", response_model=list[CompletionItem])
def list_my_completions(
    principal: Principal = Depends(require_permission(Permission.LEARNING_READ)),
    db: Session = Depends(get_db),
) -> list[CompletionItem]:
    completions = service.list_completions(db, principal.user_id)
    if not completions:
        return []
    # One query for every referenced course instead of one per completion.
    courses = courses_repository.get_courses_by_ids(
        db, list({completion.course_id for completion in completions})
    )
    items: list[CompletionItem] = []
    for completion in completions:
        course = courses.get(completion.course_id)
        items.append(
            CompletionItem(
                course_id=completion.course_id,
                course_title=course.title if course else "Unknown course",
                completed_at=completion.completed_at,
                completion_rule_version=completion.completion_rule_version,
            )
        )
    return items
