"""HTTP endpoints for course assignments and group course assignments.

All endpoints require ``enrollments:assign``. Learners do not call these endpoints;
they see their progress through the existing learning views.
"""

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.assignments import repository
from app.modules.assignments import service as assignments_service
from app.modules.assignments.models import CourseAssignment, GroupCourseAssignment
from app.modules.assignments.schemas import (
    AssignmentCreate,
    AssignmentDetail,
    AssignmentDueUpdate,
    AssignmentPage,
    AssignmentView,
    GroupAssignmentCreate,
    GroupAssignmentPage,
    GroupAssignmentResult,
    GroupAssignmentView,
)
from app.modules.courses.models import Course
from app.modules.enrollments.models import Enrollment
from app.modules.enrollments.schemas import EnrollmentResponse, ProgressSummary
from app.modules.enrollments.service import is_overdue as enrollment_is_overdue
from app.modules.learners.models import Learner, LearningGroup
from app.modules.progress import service as progress_service
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.security.principal import Principal

router = APIRouter(tags=["assignments"])

DerivedFilter = Literal[
    "awaiting_account", "assigned", "in_progress", "completed", "withdrawn", "cancelled"
]

_DOMAIN_ERRORS = (
    assignments_service.AssignmentNotFoundError,
    assignments_service.GroupAssignmentNotFoundError,
    assignments_service.CourseNotFoundError,
    assignments_service.CourseNotAssignableError,
    assignments_service.LearnerNotFoundError,
    assignments_service.LearnerInactiveError,
    assignments_service.GroupNotFoundError,
    assignments_service.GroupInactiveError,
    assignments_service.DuplicateAssignmentError,
    assignments_service.DuplicateGroupAssignmentError,
    assignments_service.AssignmentNotActiveError,
    assignments_service.GroupAssignmentNotActiveError,
)


def _to_http(exc: Exception) -> HTTPException:
    def conflict(detail: str) -> HTTPException:
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    def missing(detail: str) -> HTTPException:
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

    if isinstance(exc, assignments_service.AssignmentNotFoundError):
        return missing("Assignment not found.")
    if isinstance(exc, assignments_service.GroupAssignmentNotFoundError):
        return missing("Group assignment not found.")
    if isinstance(exc, assignments_service.CourseNotFoundError):
        return missing("Course not found.")
    if isinstance(exc, assignments_service.CourseNotAssignableError):
        return conflict(
            "Only published courses can be assigned. Draft and archived courses cannot."
        )
    if isinstance(exc, assignments_service.LearnerNotFoundError):
        return missing("Learner not found.")
    if isinstance(exc, assignments_service.LearnerInactiveError):
        return conflict("This learner record is inactive and cannot receive new assignments.")
    if isinstance(exc, assignments_service.GroupNotFoundError):
        return missing("Learning group not found.")
    if isinstance(exc, assignments_service.GroupInactiveError):
        return conflict("This learning group is inactive.")
    if isinstance(exc, assignments_service.DuplicateAssignmentError):
        return conflict("This learner already has an active assignment to this course.")
    if isinstance(exc, assignments_service.DuplicateGroupAssignmentError):
        return conflict("This group already has an active assignment to this course.")
    if isinstance(exc, assignments_service.AssignmentNotActiveError):
        return conflict("This assignment is already cancelled.")
    if isinstance(exc, assignments_service.GroupAssignmentNotActiveError):
        return conflict("This group assignment is already cancelled.")
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected.")


def _learner_name(learner: Learner) -> str:
    return learner.full_name


def _assignment_view(
    assignment: CourseAssignment,
    course: Course,
    learner: Learner,
    enrollment: Enrollment | None,
    group: LearningGroup | None,
    *,
    now: datetime,
) -> AssignmentView:
    return AssignmentView(
        id=assignment.id,
        course_id=course.id,
        course_title=course.title,
        learner_id=learner.id,
        learner_employee_id=learner.employee_id,
        learner_name=_learner_name(learner),
        group_assignment_id=assignment.group_assignment_id,
        group_id=group.id if group is not None else None,
        group_name=group.name if group is not None else None,
        source=assignment.source,
        status=assignment.status,
        derived_status=assignments_service.derived_status(assignment, enrollment),
        enrollment_id=enrollment.id if enrollment is not None else None,
        due_at=assignment.due_at,
        overdue=assignments_service.is_overdue(assignment, enrollment, now=now),
        assigned_at=assignment.assigned_at,
        cancelled_at=assignment.cancelled_at,
        cancel_reason=assignment.cancel_reason,
    )


def _group_view(
    group_assignment: GroupCourseAssignment, course: Course, group: LearningGroup
) -> GroupAssignmentView:
    return GroupAssignmentView(
        id=group_assignment.id,
        course_id=course.id,
        course_title=course.title,
        group_id=group.id,
        group_name=group.name,
        status=group_assignment.status,
        due_at=group_assignment.due_at,
        assigned_at=group_assignment.assigned_at,
        cancelled_at=group_assignment.cancelled_at,
        cancel_reason=group_assignment.cancel_reason,
    )


def _load_view(db: Session, assignment_id: uuid.UUID) -> AssignmentView:
    row = repository.get_assignment_detail_row(db, assignment_id)
    if row is None:  # pragma: no cover - the row was just written or read
        raise assignments_service.AssignmentNotFoundError(str(assignment_id))
    assignment, course, learner, enrollment, _group_assignment, group = row
    return _assignment_view(assignment, course, learner, enrollment, group, now=datetime.now(UTC))


# --------------------------------------------------------------------------- #
# Individual assignments
# --------------------------------------------------------------------------- #
@router.post(
    "/courses/{course_id}/assignments",
    response_model=AssignmentView,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    course_id: uuid.UUID,
    payload: AssignmentCreate,
    principal: Principal = Depends(require_permission(Permission.ENROLLMENTS_ASSIGN)),
    db: Session = Depends(get_db),
) -> AssignmentView:
    try:
        assignment = assignments_service.create_individual_assignment(
            db,
            actor=principal,
            course_id=course_id,
            learner_id=payload.learner_id,
            due_at=payload.due_at,
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return _load_view(db, assignment.id)


@router.get("/assignments", response_model=AssignmentPage)
def list_assignments(
    course_id: uuid.UUID | None = None,
    learner_id: uuid.UUID | None = None,
    group_id: uuid.UUID | None = None,
    assignment_status: Literal["active", "cancelled"] | None = Query(default=None, alias="status"),
    derived: DerivedFilter | None = None,
    overdue: bool | None = None,
    search: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_permission(Permission.ENROLLMENTS_ASSIGN)),
    db: Session = Depends(get_db),
) -> AssignmentPage:
    now = datetime.now(UTC)
    rows, total = repository.list_assignments(
        db,
        course_id=course_id,
        learner_id=learner_id,
        group_id=group_id,
        status=assignment_status,
        derived=derived,
        overdue=overdue,
        search=search,
        now=now,
        limit=limit,
        offset=offset,
    )
    items = [
        _assignment_view(assignment, course, learner, enrollment, group, now=now)
        for assignment, course, learner, enrollment, group in rows
    ]
    return AssignmentPage(items=items, total=total, limit=limit, offset=offset)


@router.get("/assignments/{assignment_id}", response_model=AssignmentDetail)
def get_assignment(
    assignment_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.ENROLLMENTS_ASSIGN)),
    db: Session = Depends(get_db),
) -> AssignmentDetail:
    row = repository.get_assignment_detail_row(db, assignment_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
    assignment, course, learner, enrollment, _group_assignment, group = row
    now = datetime.now(UTC)
    view = _assignment_view(assignment, course, learner, enrollment, group, now=now)
    progress = None
    if enrollment is not None:
        total, completed, percent, is_complete = progress_service.progress_summary(
            db, user_id=enrollment.learner_id, course_id=course.id
        )
        progress = ProgressSummary(
            required_lessons=total,
            completed_lessons=completed,
            percent=percent,
            is_complete=is_complete,
        )
    return AssignmentDetail(
        **view.model_dump(),
        enrollment=EnrollmentResponse(
            id=enrollment.id,
            learner_id=enrollment.learner_id,
            course_id=enrollment.course_id,
            assignment_source=enrollment.assignment_source,
            assigned_by=enrollment.assigned_by,
            assigned_at=enrollment.assigned_at,
            due_at=enrollment.due_at,
            status=enrollment.status,
            completed_at=enrollment.completed_at,
            overdue=enrollment_is_overdue(enrollment, now=now),
        )
        if enrollment is not None
        else None,
        progress=progress,
    )


@router.patch("/assignments/{assignment_id}", response_model=AssignmentView)
def update_assignment(
    assignment_id: uuid.UUID,
    payload: AssignmentDueUpdate,
    principal: Principal = Depends(require_permission(Permission.ENROLLMENTS_ASSIGN)),
    db: Session = Depends(get_db),
) -> AssignmentView:
    try:
        assignment = assignments_service.update_assignment_due_date(
            db,
            actor=principal,
            assignment_id=assignment_id,
            due_at=payload.due_at,
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return _load_view(db, assignment.id)


@router.post("/assignments/{assignment_id}/cancel", response_model=AssignmentView)
def cancel_assignment(
    assignment_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.ENROLLMENTS_ASSIGN)),
    db: Session = Depends(get_db),
) -> AssignmentView:
    try:
        assignment = assignments_service.cancel_assignment(
            db, actor=principal, assignment_id=assignment_id
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    return _load_view(db, assignment.id)


# --------------------------------------------------------------------------- #
# Group course assignments
# --------------------------------------------------------------------------- #
@router.post(
    "/courses/{course_id}/group-assignments",
    response_model=GroupAssignmentResult,
    status_code=status.HTTP_201_CREATED,
)
def create_group_assignment(
    course_id: uuid.UUID,
    payload: GroupAssignmentCreate,
    principal: Principal = Depends(require_permission(Permission.ENROLLMENTS_ASSIGN)),
    db: Session = Depends(get_db),
) -> GroupAssignmentResult:
    try:
        result = assignments_service.create_group_assignment(
            db,
            actor=principal,
            course_id=course_id,
            group_id=payload.group_id,
            due_at=payload.due_at,
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    row = db.get(GroupCourseAssignment, result.group_assignment.id)
    course = db.get(Course, course_id)
    group = db.get(LearningGroup, payload.group_id)
    return GroupAssignmentResult(
        group_assignment=_group_view(row, course, group),
        created=result.created,
        skipped_existing=result.skipped_existing,
        skipped_inactive=result.skipped_inactive,
    )


@router.get("/group-assignments", response_model=GroupAssignmentPage)
def list_group_assignments(
    course_id: uuid.UUID | None = None,
    group_id: uuid.UUID | None = None,
    assignment_status: Literal["active", "cancelled"] | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    principal: Principal = Depends(require_permission(Permission.ENROLLMENTS_ASSIGN)),
    db: Session = Depends(get_db),
) -> GroupAssignmentPage:
    rows, total = repository.list_group_assignments(
        db,
        course_id=course_id,
        group_id=group_id,
        status=assignment_status,
        limit=limit,
        offset=offset,
    )
    items = [_group_view(ga, course, group) for ga, course, group in rows]
    return GroupAssignmentPage(items=items, total=total, limit=limit, offset=offset)


@router.post("/group-assignments/{group_assignment_id}/cancel", response_model=GroupAssignmentView)
def cancel_group_assignment(
    group_assignment_id: uuid.UUID,
    principal: Principal = Depends(require_permission(Permission.ENROLLMENTS_ASSIGN)),
    db: Session = Depends(get_db),
) -> GroupAssignmentView:
    try:
        group_assignment = assignments_service.cancel_group_assignment(
            db, actor=principal, group_assignment_id=group_assignment_id
        )
    except _DOMAIN_ERRORS as exc:
        raise _to_http(exc) from None
    course = db.get(Course, group_assignment.course_id)
    group = db.get(LearningGroup, group_assignment.group_id)
    return _group_view(group_assignment, course, group)
