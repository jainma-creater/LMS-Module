"""Database queries for course assignments and group course assignments.

Derived statuses (``awaiting_account``, ``overdue``) are expressed as SQL
conditions here so that filtering and pagination totals stay correct.
"""

import uuid
from datetime import datetime

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.modules.assignments.models import (
    AssignmentStatus,
    CourseAssignment,
    GroupCourseAssignment,
)
from app.modules.courses.models import Course
from app.modules.enrollments.models import Enrollment, EnrollmentStatus
from app.modules.learners.models import Learner, LearningGroup

AWAITING_ACCOUNT = "awaiting_account"
CLOSED_ENROLLMENT_STATES = (EnrollmentStatus.COMPLETED, EnrollmentStatus.WITHDRAWN)

# (assignment, course, learner, enrollment or None, group or None)
AssignmentRow = tuple[CourseAssignment, Course, Learner, Enrollment | None, LearningGroup | None]
# (assignment, course, learner, enrollment, group assignment, group), each optional
DetailRow = tuple[
    CourseAssignment,
    Course,
    Learner,
    Enrollment | None,
    GroupCourseAssignment | None,
    LearningGroup | None,
]


def get_assignment(db: Session, assignment_id: uuid.UUID) -> CourseAssignment | None:
    return db.get(CourseAssignment, assignment_id)


def get_group_assignment(
    db: Session, group_assignment_id: uuid.UUID
) -> GroupCourseAssignment | None:
    return db.get(GroupCourseAssignment, group_assignment_id)


def get_active_assignment(
    db: Session, course_id: uuid.UUID, learner_id: uuid.UUID
) -> CourseAssignment | None:
    stmt = select(CourseAssignment).where(
        CourseAssignment.course_id == course_id,
        CourseAssignment.learner_id == learner_id,
        CourseAssignment.status == AssignmentStatus.ACTIVE,
    )
    return db.execute(stmt).scalar_one_or_none()


def get_active_group_assignment(
    db: Session, group_id: uuid.UUID, course_id: uuid.UUID
) -> GroupCourseAssignment | None:
    stmt = select(GroupCourseAssignment).where(
        GroupCourseAssignment.group_id == group_id,
        GroupCourseAssignment.course_id == course_id,
        GroupCourseAssignment.status == AssignmentStatus.ACTIVE,
    )
    return db.execute(stmt).scalar_one_or_none()


def list_active_group_assignments_for_group(
    db: Session, group_id: uuid.UUID
) -> list[GroupCourseAssignment]:
    stmt = select(GroupCourseAssignment).where(
        GroupCourseAssignment.group_id == group_id,
        GroupCourseAssignment.status == AssignmentStatus.ACTIVE,
    )
    return list(db.execute(stmt).scalars())


def list_active_group_derived_for_learner(
    db: Session, *, learner_id: uuid.UUID, group_id: uuid.UUID
) -> list[CourseAssignment]:
    stmt = (
        select(CourseAssignment)
        .join(
            GroupCourseAssignment,
            GroupCourseAssignment.id == CourseAssignment.group_assignment_id,
        )
        .where(
            CourseAssignment.learner_id == learner_id,
            CourseAssignment.status == AssignmentStatus.ACTIVE,
            GroupCourseAssignment.group_id == group_id,
        )
    )
    return list(db.execute(stmt).scalars())


def list_active_derived_for_group_assignment(
    db: Session, group_assignment_id: uuid.UUID
) -> list[CourseAssignment]:
    stmt = select(CourseAssignment).where(
        CourseAssignment.group_assignment_id == group_assignment_id,
        CourseAssignment.status == AssignmentStatus.ACTIVE,
    )
    return list(db.execute(stmt).scalars())


def list_active_unlinked_for_learner(db: Session, learner_id: uuid.UUID) -> list[CourseAssignment]:
    stmt = select(CourseAssignment).where(
        CourseAssignment.learner_id == learner_id,
        CourseAssignment.status == AssignmentStatus.ACTIVE,
        CourseAssignment.enrollment_id.is_(None),
    )
    return list(db.execute(stmt).scalars())


def count_group_members_linked_to_course(db: Session, group_assignment_id: uuid.UUID) -> int:
    stmt = select(func.count(CourseAssignment.id)).where(
        CourseAssignment.group_assignment_id == group_assignment_id
    )
    return db.execute(stmt).scalar_one()


def _derived_condition(derived: str):
    if derived == "cancelled":
        return CourseAssignment.status == AssignmentStatus.CANCELLED
    if derived == AWAITING_ACCOUNT:
        return and_(
            CourseAssignment.status == AssignmentStatus.ACTIVE,
            CourseAssignment.enrollment_id.is_(None),
        )
    return and_(
        CourseAssignment.status == AssignmentStatus.ACTIVE,
        Enrollment.status == derived,
    )


def _overdue_condition(now: datetime):
    return and_(
        CourseAssignment.status == AssignmentStatus.ACTIVE,
        CourseAssignment.due_at.is_not(None),
        CourseAssignment.due_at < now,
        or_(
            CourseAssignment.enrollment_id.is_(None),
            Enrollment.status.not_in(CLOSED_ENROLLMENT_STATES),
        ),
    )


def list_assignments(
    db: Session,
    *,
    course_id: uuid.UUID | None,
    learner_id: uuid.UUID | None,
    group_id: uuid.UUID | None,
    status: str | None,
    derived: str | None,
    overdue: bool | None,
    search: str | None,
    now: datetime,
    limit: int,
    offset: int,
) -> tuple[list[AssignmentRow], int]:
    conditions = []
    if course_id is not None:
        conditions.append(CourseAssignment.course_id == course_id)
    if learner_id is not None:
        conditions.append(CourseAssignment.learner_id == learner_id)
    if group_id is not None:
        conditions.append(GroupCourseAssignment.group_id == group_id)
    if status:
        conditions.append(CourseAssignment.status == status)
    if derived:
        conditions.append(_derived_condition(derived))
    if overdue is True:
        conditions.append(_overdue_condition(now))
    elif overdue is False:
        conditions.append(~_overdue_condition(now))
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                Learner.first_name.ilike(pattern),
                Learner.last_name.ilike(pattern),
                Learner.employee_id.ilike(pattern),
                Course.title.ilike(pattern),
            )
        )

    base = (
        select(CourseAssignment, Course, Learner, Enrollment, LearningGroup)
        .join(Course, Course.id == CourseAssignment.course_id)
        .join(Learner, Learner.id == CourseAssignment.learner_id)
        .outerjoin(Enrollment, Enrollment.id == CourseAssignment.enrollment_id)
        .outerjoin(
            GroupCourseAssignment,
            GroupCourseAssignment.id == CourseAssignment.group_assignment_id,
        )
        .outerjoin(LearningGroup, LearningGroup.id == GroupCourseAssignment.group_id)
    )
    count_stmt = (
        select(func.count(CourseAssignment.id))
        .select_from(CourseAssignment)
        .join(Course, Course.id == CourseAssignment.course_id)
        .join(Learner, Learner.id == CourseAssignment.learner_id)
        .outerjoin(Enrollment, Enrollment.id == CourseAssignment.enrollment_id)
        .outerjoin(
            GroupCourseAssignment,
            GroupCourseAssignment.id == CourseAssignment.group_assignment_id,
        )
    )
    if conditions:
        base = base.where(*conditions)
        count_stmt = count_stmt.where(*conditions)
    stmt = (
        base.order_by(CourseAssignment.assigned_at.desc(), CourseAssignment.id.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = [tuple(row) for row in db.execute(stmt).all()]
    total = db.execute(count_stmt).scalar_one()
    return rows, total


def get_assignment_detail_row(db: Session, assignment_id: uuid.UUID) -> DetailRow | None:
    stmt = (
        select(CourseAssignment, Course, Learner, Enrollment, GroupCourseAssignment, LearningGroup)
        .join(Course, Course.id == CourseAssignment.course_id)
        .join(Learner, Learner.id == CourseAssignment.learner_id)
        .outerjoin(Enrollment, Enrollment.id == CourseAssignment.enrollment_id)
        .outerjoin(
            GroupCourseAssignment,
            GroupCourseAssignment.id == CourseAssignment.group_assignment_id,
        )
        .outerjoin(LearningGroup, LearningGroup.id == GroupCourseAssignment.group_id)
        .where(CourseAssignment.id == assignment_id)
    )
    row = db.execute(stmt).first()
    return None if row is None else tuple(row)


def list_group_assignments(
    db: Session,
    *,
    course_id: uuid.UUID | None,
    group_id: uuid.UUID | None,
    status: str | None,
    limit: int,
    offset: int,
) -> tuple[list[tuple[GroupCourseAssignment, Course, LearningGroup]], int]:
    conditions = []
    if course_id is not None:
        conditions.append(GroupCourseAssignment.course_id == course_id)
    if group_id is not None:
        conditions.append(GroupCourseAssignment.group_id == group_id)
    if status:
        conditions.append(GroupCourseAssignment.status == status)
    stmt = (
        select(GroupCourseAssignment, Course, LearningGroup)
        .join(Course, Course.id == GroupCourseAssignment.course_id)
        .join(LearningGroup, LearningGroup.id == GroupCourseAssignment.group_id)
    )
    count_stmt = select(func.count(GroupCourseAssignment.id))
    if conditions:
        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)
    stmt = stmt.order_by(GroupCourseAssignment.assigned_at.desc(), GroupCourseAssignment.id.desc())
    stmt = stmt.limit(limit).offset(offset)
    rows = [tuple(row) for row in db.execute(stmt).all()]
    total = db.execute(count_stmt).scalar_one()
    return rows, total
