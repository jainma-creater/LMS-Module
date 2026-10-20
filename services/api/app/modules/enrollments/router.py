"""HTTP endpoints for enrollment and assignment.

Assignments require ``enrollments:assign``. Learners read their own enrollment and
learning views; identity always comes from the authenticated principal.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.courses import repository as courses_repository
from app.modules.enrollments import service
from app.modules.enrollments.schemas import (
    CourseEnrollmentsResponse,
    CourseSummary,
    EnrollmentCreate,
    EnrollmentDueUpdate,
    EnrollmentResponse,
    MyLearningItem,
    ProgressSummary,
)
from app.modules.progress import service as progress_service
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.security.principal import Principal

router = APIRouter(tags=["enrollments"])

_DOMAIN_ERRORS = (
    service.EnrollmentNotFoundError,
    service.AlreadyEnrolledError,
    service.CourseNotEnrollableError,
    service.LearnerNotFoundError,
)


def _to_http(exc: Exception) -> HTTPException:
    if isinstance(exc, service.EnrollmentNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found.")
    if isinstance(exc, service.CourseNotEnrollableError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course is not available for enrollment."
        )
    if isinstance(exc, service.LearnerNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found.")
    if isinstance(exc, service.AlreadyEnrolledError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Learner already has an active enrollment in this course.",
        )
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected.")


def _response(enrollment) -> EnrollmentResponse:
    return EnrollmentResponse(
        id=enrollment.id,
        learner_id=enrollment.learner_id,
        course_id=enrollment.course_id,
        assignment_source=enrollment.assignment_source,
        assigned_by=enrollment.assigned_by,
        assigned_at=enrollment.assigned_at,
        due_at=enrollment.due_at,
        status=enrollment.status,
        completed_at=enrollment.completed_at,
        overdue=service.is_overdue(enrollment),
    )


@router.post(
    "/courses/{course_id}/enrollments",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_enrollment(
    course_id: uuid.UUID,
    payload: EnrollmentCreate,
    principal: Principal = Depends(require_permission(Permission.ENROLLMENTS_ASSIGN)),
    db: Session = Depends(get_db),
) -> EnrollmentResponse:
    try:
        enrollment = service.assign(
            db,
            actor=principal,
            course_id=course_id,
            learner_id=payload.learner_id,
            due_at=payload.due_at,
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return _response(enrollment)


@router.get("/courses/{course_id}/enrollments", response_model=CourseEnrollmentsResponse)
def list_course_enrollments(
    course_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.ENROLLMENTS_ASSIGN)),
    db: Session = Depends(get_db),
) -> CourseEnrollmentsResponse:
    if courses_repository.get_course(db, course_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found.")
    enrollments = service.list_for_course(db, course_id)
    return CourseEnrollmentsResponse(
        course_id=course_id, enrollments=[_response(item) for item in enrollments]
    )


@router.get("/me/learning", response_model=list[MyLearningItem])
def my_learning(
    principal: Principal = Depends(require_permission(Permission.LEARNING_READ)),
    db: Session = Depends(get_db),
) -> list[MyLearningItem]:
    enrollments = service.list_for_learner(db, principal.user_id)
    if not enrollments:
        return []
    course_ids = list({enrollment.course_id for enrollment in enrollments})
    courses = courses_repository.get_courses_by_ids(db, course_ids)
    summaries = progress_service.progress_summaries(
        db, user_id=principal.user_id, course_ids=course_ids
    )

    items: list[MyLearningItem] = []
    for enrollment in enrollments:
        course = courses.get(enrollment.course_id)
        if course is None:
            continue
        total, completed, percent, is_complete = summaries.get(
            enrollment.course_id, (0, 0, 0, False)
        )
        items.append(
            MyLearningItem(
                enrollment=_response(enrollment),
                course=CourseSummary.model_validate(course),
                progress=ProgressSummary(
                    required_lessons=total,
                    completed_lessons=completed,
                    percent=percent,
                    is_complete=is_complete,
                ),
            )
        )
    return items


@router.get("/enrollments/{enrollment_id}", response_model=EnrollmentResponse)
def get_enrollment(
    enrollment_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.LEARNING_READ)),
    db: Session = Depends(get_db),
) -> EnrollmentResponse:
    try:
        enrollment = service.get_enrollment_for(
            db, principal=principal, enrollment_id=enrollment_id
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return _response(enrollment)


@router.patch("/enrollments/{enrollment_id}", response_model=EnrollmentResponse)
def update_enrollment(
    enrollment_id: uuid.UUID,
    payload: EnrollmentDueUpdate,
    principal: Principal = Depends(require_permission(Permission.ENROLLMENTS_ASSIGN)),
    db: Session = Depends(get_db),
) -> EnrollmentResponse:
    try:
        enrollment = service.update_due_date(
            db, actor=principal, enrollment_id=enrollment_id, due_at=payload.due_at
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return _response(enrollment)
