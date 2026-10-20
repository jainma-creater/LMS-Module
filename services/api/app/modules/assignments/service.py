"""Business logic for course assignments and learning-group course assignments.

Rules implemented here (see docs/LLD.md, "Assignments"):

- Only **published** courses can be newly assigned. Draft and archived courses
  return a conflict. Existing assignments are not changed when a course is archived.
- Only **active** learners receive new assignments. Inactive learners keep their
  history but are skipped by group expansion and cannot be assigned directly.
- At most one **active** assignment per learner and course. Group expansion skips
  learners who already have one, so it is idempotent.
- **Group membership changes**
  - Joining a group applies every active group assignment to the new member.
  - Leaving a group cancels that member's active assignments that came from the
    group. Their unfinished enrollments are withdrawn. Completed work is kept.
  - Cancelling a group assignment cancels all its active member assignments in the
    same way. Individual assignments are never touched by group changes.
- **Enrollment linkage.** An assignment creates or links the enrollment (progress
  record) for the learner's linked user. Without a linked user the assignment is
  ``awaiting_account`` until the learner is linked. The assignment's due date is
  authoritative while linked.
- Cancelling never deletes history. Rows are kept with ``status='cancelled'``.

Functions that change several rows do NOT commit. The caller commits, so the whole
operation (including audit events) is atomic. Public entry points commit.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.assignments import repository
from app.modules.assignments.models import (
    AssignmentSource,
    AssignmentStatus,
    CourseAssignment,
    GroupCourseAssignment,
)
from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditOutcome
from app.modules.courses import repository as courses_repository
from app.modules.courses.models import Course, CourseStatus
from app.modules.enrollments import repository as enrollments_repository
from app.modules.enrollments import service as enrollments_service
from app.modules.enrollments.models import (
    AssignmentSource as EnrollmentSource,
)
from app.modules.enrollments.models import (
    Enrollment,
    EnrollmentStatus,
)
from app.modules.learners import repository as learners_repository
from app.modules.learners.models import GroupStatus, Learner, LearnerStatus, LearningGroup
from app.security.principal import Principal

REASON_CANCELLED_BY_ADMIN = "cancelled_by_admin"
REASON_GROUP_MEMBERSHIP_REMOVED = "group_membership_removed"
REASON_GROUP_ASSIGNMENT_CANCELLED = "group_assignment_cancelled"

# Derived status values exposed to the API, in addition to enrollment statuses.
DERIVED_AWAITING_ACCOUNT = "awaiting_account"
DERIVED_CANCELLED = "cancelled"


class AssignmentNotFoundError(Exception):
    """No course assignment exists for the given identifier."""


class GroupAssignmentNotFoundError(Exception):
    """No group course assignment exists for the given identifier."""


class CourseNotFoundError(Exception):
    """No course exists for the given identifier."""


class CourseNotAssignableError(Exception):
    """The course is a draft or archived and cannot be newly assigned."""


class LearnerNotFoundError(Exception):
    """No learner record exists for the given identifier."""


class LearnerInactiveError(Exception):
    """The learner record is inactive and cannot receive new assignments."""


class GroupNotFoundError(Exception):
    """No learning group exists for the given identifier."""


class GroupInactiveError(Exception):
    """The learning group is inactive and cannot receive new assignments or members."""


class DuplicateAssignmentError(Exception):
    """The learner already has an active assignment to this course."""


class DuplicateGroupAssignmentError(Exception):
    """The group already has an active assignment to this course."""


class AssignmentNotActiveError(Exception):
    """The assignment is already cancelled."""


class GroupAssignmentNotActiveError(Exception):
    """The group assignment is already cancelled."""


@dataclass(frozen=True)
class GroupAssignmentResult:
    group_assignment: GroupCourseAssignment
    created: int
    skipped_existing: int
    skipped_inactive: int


def _now() -> datetime:
    return datetime.now(UTC)


def derived_status(assignment: CourseAssignment, enrollment: Enrollment | None) -> str:
    """Single status a manager reads: assignment state first, then progress."""
    if assignment.status == AssignmentStatus.CANCELLED:
        return DERIVED_CANCELLED
    if enrollment is None:
        return DERIVED_AWAITING_ACCOUNT
    return enrollment.status


def is_overdue(
    assignment: CourseAssignment, enrollment: Enrollment | None, *, now: datetime
) -> bool:
    if assignment.due_at is None or assignment.status != AssignmentStatus.ACTIVE:
        return False
    if enrollment is not None and enrollment.status in (
        EnrollmentStatus.COMPLETED,
        EnrollmentStatus.WITHDRAWN,
    ):
        return False
    due_at = assignment.due_at
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=UTC)
    return due_at < now


def _require_assignable_course(db: Session, course_id: uuid.UUID) -> Course:
    course = courses_repository.get_course(db, course_id)
    if course is None:
        raise CourseNotFoundError(str(course_id))
    if course.status != CourseStatus.PUBLISHED:
        raise CourseNotAssignableError(str(course_id))
    return course


def _require_learner(db: Session, learner_id: uuid.UUID) -> Learner:
    learner = learners_repository.get_learner(db, learner_id)
    if learner is None:
        raise LearnerNotFoundError(str(learner_id))
    return learner


def _require_group(db: Session, group_id: uuid.UUID) -> LearningGroup:
    group = learners_repository.get_group(db, group_id)
    if group is None:
        raise GroupNotFoundError(str(group_id))
    return group


def _link_enrollment(
    db: Session,
    *,
    actor: Principal,
    assignment: CourseAssignment,
    learner: Learner,
    enrollment_source: str,
) -> None:
    """Create or link the progress enrollment for a learner with a linked user."""
    if learner.user_id is None:
        assignment.enrollment_id = None
        return
    enrollment = enrollments_repository.get_active_enrollment(
        db, learner.user_id, assignment.course_id
    )
    if enrollment is None:
        enrollment = Enrollment(
            learner_id=learner.user_id,
            course_id=assignment.course_id,
            assignment_source=enrollment_source,
            assigned_by=actor.user_id,
            due_at=assignment.due_at,
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
            metadata={
                "course_id": str(assignment.course_id),
                "assignment_id": str(assignment.id),
            },
        )
    else:
        # The assignment is authoritative for the due date while it is linked.
        enrollments_service.set_due_date(enrollment, due_at=assignment.due_at)
    assignment.enrollment_id = enrollment.id


def _create_assignment(
    db: Session,
    *,
    actor: Principal,
    course: Course,
    learner: Learner,
    source: str,
    group_assignment_id: uuid.UUID | None,
    due_at: datetime | None,
) -> CourseAssignment:
    assignment = CourseAssignment(
        course_id=course.id,
        learner_id=learner.id,
        source=source,
        group_assignment_id=group_assignment_id,
        due_at=due_at,
        status=AssignmentStatus.ACTIVE,
        assigned_by=actor.user_id,
    )
    db.add(assignment)
    db.flush()
    enrollment_source = (
        EnrollmentSource.GROUP if source == AssignmentSource.GROUP else EnrollmentSource.ADMIN
    )
    _link_enrollment(
        db,
        actor=actor,
        assignment=assignment,
        learner=learner,
        enrollment_source=enrollment_source,
    )
    audit_service.record_event(
        db,
        action=audit_service.ACTION_ASSIGNMENT_CREATED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="assignment",
        target_id=str(assignment.id),
        metadata={
            "course_id": str(course.id),
            "learner_id": str(learner.id),
            "source": source,
            "group_assignment_id": str(group_assignment_id) if group_assignment_id else None,
        },
    )
    return assignment


def _assign_from_group(
    db: Session,
    *,
    actor: Principal,
    course: Course,
    learner: Learner,
    group_assignment: GroupCourseAssignment,
) -> str:
    """Apply one group assignment to one learner. Returns created/existing/inactive."""
    if learner.status != LearnerStatus.ACTIVE:
        return "inactive"
    if repository.get_active_assignment(db, course.id, learner.id) is not None:
        return "existing"
    _create_assignment(
        db,
        actor=actor,
        course=course,
        learner=learner,
        source=AssignmentSource.GROUP,
        group_assignment_id=group_assignment.id,
        due_at=group_assignment.due_at,
    )
    return "created"


def _end_assignment(
    db: Session, *, actor: Principal, assignment: CourseAssignment, reason: str, now: datetime
) -> None:
    """Cancel an active assignment and withdraw its unfinished enrollment."""
    assignment.status = AssignmentStatus.CANCELLED
    assignment.cancelled_at = now
    assignment.cancel_reason = reason
    audit_service.record_event(
        db,
        action=audit_service.ACTION_ASSIGNMENT_CANCELLED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="assignment",
        target_id=str(assignment.id),
        metadata={"reason": reason},
    )
    if assignment.enrollment_id is None:
        return
    enrollment = enrollments_repository.get_enrollment(db, assignment.enrollment_id)
    if enrollment is None or enrollment.status in (
        EnrollmentStatus.COMPLETED,
        EnrollmentStatus.WITHDRAWN,
    ):
        return
    enrollments_service.withdraw(db, enrollment, when=now)
    audit_service.record_event(
        db,
        action=audit_service.ACTION_ENROLLMENT_WITHDRAWN,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="enrollment",
        target_id=str(enrollment.id),
        metadata={"reason": reason},
    )


def _commit_or_duplicate(db: Session, error: type[Exception], message: str) -> None:
    """Commit, translating a database uniqueness violation into a domain error.

    The partial unique indexes are the final guard against concurrent duplicates;
    the pre-checks above only produce friendlier errors in the common case.
    """
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise error(message) from None


# --------------------------------------------------------------------------- #
# Individual assignments
# --------------------------------------------------------------------------- #
def create_individual_assignment(
    db: Session,
    *,
    actor: Principal,
    course_id: uuid.UUID,
    learner_id: uuid.UUID,
    due_at: datetime | None,
) -> CourseAssignment:
    course = _require_assignable_course(db, course_id)
    learner = _require_learner(db, learner_id)
    if learner.status != LearnerStatus.ACTIVE:
        raise LearnerInactiveError(str(learner_id))
    if repository.get_active_assignment(db, course.id, learner.id) is not None:
        raise DuplicateAssignmentError(str(learner_id))

    assignment = _create_assignment(
        db,
        actor=actor,
        course=course,
        learner=learner,
        source=AssignmentSource.INDIVIDUAL,
        group_assignment_id=None,
        due_at=due_at,
    )
    _commit_or_duplicate(db, DuplicateAssignmentError, str(learner_id))
    db.refresh(assignment)
    return assignment


def cancel_assignment(
    db: Session, *, actor: Principal, assignment_id: uuid.UUID
) -> CourseAssignment:
    assignment = repository.get_assignment(db, assignment_id)
    if assignment is None:
        raise AssignmentNotFoundError(str(assignment_id))
    if assignment.status != AssignmentStatus.ACTIVE:
        raise AssignmentNotActiveError(str(assignment_id))
    _end_assignment(
        db,
        actor=actor,
        assignment=assignment,
        reason=REASON_CANCELLED_BY_ADMIN,
        now=_now(),
    )
    db.commit()
    db.refresh(assignment)
    return assignment


def update_assignment_due_date(
    db: Session,
    *,
    actor: Principal,
    assignment_id: uuid.UUID,
    due_at: datetime | None,
) -> CourseAssignment:
    assignment = repository.get_assignment(db, assignment_id)
    if assignment is None:
        raise AssignmentNotFoundError(str(assignment_id))
    if assignment.status != AssignmentStatus.ACTIVE:
        raise AssignmentNotActiveError(str(assignment_id))
    assignment.due_at = due_at
    if assignment.enrollment_id is not None:
        enrollment = enrollments_repository.get_enrollment(db, assignment.enrollment_id)
        if enrollment is not None and enrollment.status not in (
            EnrollmentStatus.COMPLETED,
            EnrollmentStatus.WITHDRAWN,
        ):
            enrollments_service.set_due_date(enrollment, due_at=due_at)
    audit_service.record_event(
        db,
        action=audit_service.ACTION_ASSIGNMENT_UPDATED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="assignment",
        target_id=str(assignment.id),
        metadata={"field": "due_at"},
    )
    db.commit()
    db.refresh(assignment)
    return assignment


# --------------------------------------------------------------------------- #
# Group assignments
# --------------------------------------------------------------------------- #
def create_group_assignment(
    db: Session,
    *,
    actor: Principal,
    course_id: uuid.UUID,
    group_id: uuid.UUID,
    due_at: datetime | None,
) -> GroupAssignmentResult:
    course = _require_assignable_course(db, course_id)
    group = _require_group(db, group_id)
    if group.status != GroupStatus.ACTIVE:
        raise GroupInactiveError(str(group_id))
    if repository.get_active_group_assignment(db, group.id, course.id) is not None:
        raise DuplicateGroupAssignmentError(str(group_id))

    group_assignment = GroupCourseAssignment(
        group_id=group.id,
        course_id=course.id,
        due_at=due_at,
        status=AssignmentStatus.ACTIVE,
        assigned_by=actor.user_id,
    )
    db.add(group_assignment)
    db.flush()

    created = skipped_existing = skipped_inactive = 0
    for learner in learners_repository.list_active_member_learners(db, group.id):
        outcome = _assign_from_group(
            db,
            actor=actor,
            course=course,
            learner=learner,
            group_assignment=group_assignment,
        )
        if outcome == "created":
            created += 1
        elif outcome == "existing":
            skipped_existing += 1
        else:
            skipped_inactive += 1

    audit_service.record_event(
        db,
        action=audit_service.ACTION_GROUP_ASSIGNMENT_CREATED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="group_assignment",
        target_id=str(group_assignment.id),
        metadata={
            "group_id": str(group.id),
            "course_id": str(course.id),
            "created": created,
            "skipped_existing": skipped_existing,
            "skipped_inactive": skipped_inactive,
        },
    )
    _commit_or_duplicate(db, DuplicateGroupAssignmentError, str(group_id))
    db.refresh(group_assignment)
    return GroupAssignmentResult(
        group_assignment=group_assignment,
        created=created,
        skipped_existing=skipped_existing,
        skipped_inactive=skipped_inactive,
    )


def cancel_group_assignment(
    db: Session, *, actor: Principal, group_assignment_id: uuid.UUID
) -> GroupCourseAssignment:
    group_assignment = repository.get_group_assignment(db, group_assignment_id)
    if group_assignment is None:
        raise GroupAssignmentNotFoundError(str(group_assignment_id))
    if group_assignment.status != AssignmentStatus.ACTIVE:
        raise GroupAssignmentNotActiveError(str(group_assignment_id))

    now = _now()
    group_assignment.status = AssignmentStatus.CANCELLED
    group_assignment.cancelled_at = now
    group_assignment.cancel_reason = REASON_CANCELLED_BY_ADMIN
    members = repository.list_active_derived_for_group_assignment(db, group_assignment.id)
    for assignment in members:
        _end_assignment(
            db,
            actor=actor,
            assignment=assignment,
            reason=REASON_GROUP_ASSIGNMENT_CANCELLED,
            now=now,
        )
    audit_service.record_event(
        db,
        action=audit_service.ACTION_GROUP_ASSIGNMENT_CANCELLED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="group_assignment",
        target_id=str(group_assignment.id),
        metadata={"cancelled_assignments": len(members)},
    )
    db.commit()
    db.refresh(group_assignment)
    return group_assignment


# --------------------------------------------------------------------------- #
# Hooks used by learner and group changes (do not commit)
# --------------------------------------------------------------------------- #
def apply_group_assignments_to_member(
    db: Session, *, actor: Principal, group_id: uuid.UUID, learner: Learner
) -> int:
    """Apply the group's active course assignments to a newly added member."""
    created = 0
    for group_assignment in repository.list_active_group_assignments_for_group(db, group_id):
        course = courses_repository.get_course(db, group_assignment.course_id)
        if course is None or course.status != CourseStatus.PUBLISHED:
            continue
        outcome = _assign_from_group(
            db,
            actor=actor,
            course=course,
            learner=learner,
            group_assignment=group_assignment,
        )
        if outcome == "created":
            created += 1
    return created


def withdraw_group_derived_assignments(
    db: Session, *, actor: Principal, group_id: uuid.UUID, learner_id: uuid.UUID
) -> int:
    """Cancel a removed member's active assignments that came from this group."""
    now = _now()
    assignments = repository.list_active_group_derived_for_learner(
        db, learner_id=learner_id, group_id=group_id
    )
    for assignment in assignments:
        _end_assignment(
            db,
            actor=actor,
            assignment=assignment,
            reason=REASON_GROUP_MEMBERSHIP_REMOVED,
            now=now,
        )
    return len(assignments)


def materialize_for_learner(db: Session, *, actor: Principal, learner: Learner) -> int:
    """Create enrollments for a learner's awaiting assignments after account linking."""
    if learner.user_id is None:
        return 0
    linked = 0
    for assignment in repository.list_active_unlinked_for_learner(db, learner.id):
        source = (
            EnrollmentSource.GROUP
            if assignment.source == AssignmentSource.GROUP
            else EnrollmentSource.ADMIN
        )
        _link_enrollment(
            db,
            actor=actor,
            assignment=assignment,
            learner=learner,
            enrollment_source=source,
        )
        linked += 1
    return linked


__all__ = [
    "AssignmentNotActiveError",
    "AssignmentNotFoundError",
    "CourseAssignment",
    "CourseNotAssignableError",
    "CourseNotFoundError",
    "DuplicateAssignmentError",
    "DuplicateGroupAssignmentError",
    "GroupAssignmentNotActiveError",
    "GroupAssignmentNotFoundError",
    "GroupAssignmentResult",
    "GroupInactiveError",
    "GroupNotFoundError",
    "LearnerInactiveError",
    "LearnerNotFoundError",
    "apply_group_assignments_to_member",
    "cancel_assignment",
    "cancel_group_assignment",
    "create_group_assignment",
    "create_individual_assignment",
    "derived_status",
    "is_overdue",
    "materialize_for_learner",
    "update_assignment_due_date",
    "withdraw_group_derived_assignments",
]
