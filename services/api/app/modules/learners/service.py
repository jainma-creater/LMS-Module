"""Business logic for learner records, learning groups, and group membership.

Learner records are HR-style records managed by learning administrators. They are
not authentication identities. ``user_id`` links a learner to an identity user
when one exists. Linking triggers enrollment for the learner's awaiting
assignments (see ``app.modules.assignments.service``).

Membership history is kept: removing a member sets ``removed_at``. Changes to
membership also apply or withdraw group course assignments in the same transaction.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.assignments import service as assignments_service
from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditOutcome
from app.modules.learners import repository
from app.modules.learners.models import (
    GroupStatus,
    Learner,
    LearnerStatus,
    LearningGroup,
    LearningGroupMember,
)
from app.modules.learners.schemas import GroupCreate, GroupUpdate, LearnerCreate, LearnerUpdate
from app.modules.users import repository as users_repository
from app.security.principal import Principal


class LearnerNotFoundError(Exception):
    """No learner record exists for the given identifier."""


class DuplicateLearnerError(Exception):
    """Employee identifier, email, or account link is already in use."""


class UserNotFoundError(Exception):
    """The identity user to link does not exist."""


class GroupNotFoundError(Exception):
    """No learning group exists for the given identifier."""


class DuplicateGroupError(Exception):
    """A learning group with this name already exists."""


class GroupInactiveError(Exception):
    """The learning group is inactive and cannot accept new members."""


class LearnerInactiveError(Exception):
    """The learner record is inactive and cannot be added to a group."""


class DuplicateMembershipError(Exception):
    """The learner is already an active member of the group."""


class MembershipNotFoundError(Exception):
    """The learner is not an active member of the group."""


@dataclass(frozen=True)
class MembershipView:
    membership: LearningGroupMember
    learner: Learner


def _now() -> datetime:
    return datetime.now(UTC)


# --------------------------------------------------------------------------- #
# Learners
# --------------------------------------------------------------------------- #
def _ensure_learner_unique(
    db: Session,
    *,
    employee_id: str | None,
    email: str | None,
    user_id: uuid.UUID | None,
    exclude_id: uuid.UUID | None,
) -> None:
    if employee_id is not None:
        existing = repository.get_learner_by_employee_id(db, employee_id)
        if existing is not None and existing.id != exclude_id:
            raise DuplicateLearnerError("employee_id")
    if email is not None:
        existing = repository.get_learner_by_email(db, email)
        if existing is not None and existing.id != exclude_id:
            raise DuplicateLearnerError("email")
    if user_id is not None:
        existing = repository.get_learner_by_user_id(db, user_id)
        if existing is not None and existing.id != exclude_id:
            raise DuplicateLearnerError("user_id")


def create_learner(db: Session, *, actor: Principal, data: LearnerCreate) -> Learner:
    _ensure_learner_unique(
        db,
        employee_id=data.employee_id,
        email=data.email,
        user_id=None,
        exclude_id=None,
    )
    learner = Learner(
        employee_id=data.employee_id,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        department=data.department,
        business_unit=data.business_unit,
        status=data.status,
    )
    db.add(learner)
    db.flush()
    audit_service.record_event(
        db,
        action=audit_service.ACTION_LEARNER_CREATED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="learner",
        target_id=str(learner.id),
        metadata={"employee_id": learner.employee_id, "status": learner.status},
    )
    _commit_or_duplicate(db)
    db.refresh(learner)
    return learner


def get_learner(db: Session, learner_id: uuid.UUID) -> Learner:
    learner = repository.get_learner(db, learner_id)
    if learner is None:
        raise LearnerNotFoundError(str(learner_id))
    return learner


def update_learner(
    db: Session, *, actor: Principal, learner_id: uuid.UUID, data: LearnerUpdate
) -> Learner:
    learner = get_learner(db, learner_id)
    provided = data.model_fields_set

    _ensure_learner_unique(
        db,
        employee_id=data.employee_id if "employee_id" in provided else None,
        email=data.email if "email" in provided else None,
        user_id=data.user_id if "user_id" in provided else None,
        exclude_id=learner.id,
    )
    user_missing = (
        "user_id" in provided
        and data.user_id is not None
        and users_repository.get_user_by_id(db, data.user_id) is None
    )
    if user_missing:
        raise UserNotFoundError(str(data.user_id))

    changed: list[str] = []
    for field in (
        "employee_id",
        "first_name",
        "last_name",
        "email",
        "department",
        "business_unit",
        "status",
    ):
        if field in provided:
            value = getattr(data, field)
            required_fields = ("employee_id", "first_name", "last_name", "email", "status")
            if field in required_fields and value is None:
                continue
            if getattr(learner, field) != value:
                setattr(learner, field, value)
                changed.append(field)
    linked = False
    if "user_id" in provided and learner.user_id != data.user_id:
        learner.user_id = data.user_id
        changed.append("user_id")
        linked = data.user_id is not None

    if changed:
        audit_service.record_event(
            db,
            action=audit_service.ACTION_LEARNER_UPDATED,
            outcome=AuditOutcome.SUCCESS,
            actor_id=actor.user_id,
            target_type="learner",
            target_id=str(learner.id),
            metadata={"fields": sorted(changed)},
        )
    if linked:
        # A newly linked account activates the learner's awaiting assignments.
        assignments_service.materialize_for_learner(db, actor=actor, learner=learner)
    _commit_or_duplicate(db)
    db.refresh(learner)
    return learner


def list_learners(
    db: Session,
    *,
    search: str | None,
    status: str | None,
    department: str | None,
    business_unit: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Learner], int]:
    return repository.list_learners(
        db,
        search=search,
        status=status,
        department=department,
        business_unit=business_unit,
        limit=limit,
        offset=offset,
    )


def _commit_or_duplicate(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateLearnerError("record") from None


# --------------------------------------------------------------------------- #
# Learning groups
# --------------------------------------------------------------------------- #
def _ensure_group_name_free(db: Session, name: str, exclude_id: uuid.UUID | None) -> None:
    existing = repository.get_group_by_name(db, name)
    if existing is not None and existing.id != exclude_id:
        raise DuplicateGroupError(name)


def create_group(db: Session, *, actor: Principal, data: GroupCreate) -> LearningGroup:
    _ensure_group_name_free(db, data.name, exclude_id=None)
    group = LearningGroup(
        name=data.name,
        description=data.description,
        kind=data.kind,
        status=data.status,
    )
    db.add(group)
    db.flush()
    audit_service.record_event(
        db,
        action=audit_service.ACTION_GROUP_CREATED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="learning_group",
        target_id=str(group.id),
        metadata={"kind": group.kind, "status": group.status},
    )
    _commit_group_or_duplicate(db, data.name)
    db.refresh(group)
    return group


def get_group(db: Session, group_id: uuid.UUID) -> LearningGroup:
    group = repository.get_group(db, group_id)
    if group is None:
        raise GroupNotFoundError(str(group_id))
    return group


def update_group(
    db: Session, *, actor: Principal, group_id: uuid.UUID, data: GroupUpdate
) -> LearningGroup:
    group = get_group(db, group_id)
    provided = data.model_fields_set
    if "name" in provided and data.name is not None:
        _ensure_group_name_free(db, data.name, exclude_id=group.id)

    changed: list[str] = []
    for field in ("name", "description", "kind", "status"):
        if field in provided:
            value = getattr(data, field)
            if field in ("name", "kind", "status") and value is None:
                continue
            if getattr(group, field) != value:
                setattr(group, field, value)
                changed.append(field)
    if changed:
        audit_service.record_event(
            db,
            action=audit_service.ACTION_GROUP_UPDATED,
            outcome=AuditOutcome.SUCCESS,
            actor_id=actor.user_id,
            target_type="learning_group",
            target_id=str(group.id),
            metadata={"fields": sorted(changed)},
        )
    _commit_group_or_duplicate(db, group.name)
    db.refresh(group)
    return group


def _commit_group_or_duplicate(db: Session, name: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateGroupError(name) from None


def group_member_count(db: Session, group: LearningGroup) -> int:
    return repository.count_active_members(db, group.id)


def list_groups(
    db: Session,
    *,
    search: str | None,
    status: str | None,
    kind: str | None,
    limit: int,
    offset: int,
) -> tuple[list[LearningGroup], int, dict[uuid.UUID, int]]:
    items, total = repository.list_groups(
        db, search=search, status=status, kind=kind, limit=limit, offset=offset
    )
    counts = repository.active_member_counts(db, [item.id for item in items])
    return items, total, counts


# --------------------------------------------------------------------------- #
# Membership
# --------------------------------------------------------------------------- #
def add_member(
    db: Session, *, actor: Principal, group_id: uuid.UUID, learner_id: uuid.UUID
) -> LearningGroupMember:
    group = get_group(db, group_id)
    if group.status != GroupStatus.ACTIVE:
        raise GroupInactiveError(str(group_id))
    learner = get_learner(db, learner_id)
    if learner.status != LearnerStatus.ACTIVE:
        raise LearnerInactiveError(str(learner_id))
    if repository.get_active_membership(db, group.id, learner.id) is not None:
        raise DuplicateMembershipError(str(learner_id))

    membership = LearningGroupMember(
        group_id=group.id, learner_id=learner.id, added_by=actor.user_id
    )
    db.add(membership)
    db.flush()
    created = assignments_service.apply_group_assignments_to_member(
        db, actor=actor, group_id=group.id, learner=learner
    )
    audit_service.record_event(
        db,
        action=audit_service.ACTION_GROUP_MEMBER_ADDED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="learning_group",
        target_id=str(group.id),
        metadata={"learner_id": str(learner.id), "assignments_created": created},
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DuplicateMembershipError(str(learner_id)) from None
    db.refresh(membership)
    return membership


def remove_member(
    db: Session, *, actor: Principal, group_id: uuid.UUID, learner_id: uuid.UUID
) -> int:
    """Soft-remove a member. Returns how many group-derived assignments were cancelled."""
    get_group(db, group_id)
    membership = repository.get_active_membership(db, group_id, learner_id)
    if membership is None:
        raise MembershipNotFoundError(str(learner_id))
    membership.removed_at = _now()
    membership.removed_by = actor.user_id
    cancelled = assignments_service.withdraw_group_derived_assignments(
        db, actor=actor, group_id=group_id, learner_id=learner_id
    )
    audit_service.record_event(
        db,
        action=audit_service.ACTION_GROUP_MEMBER_REMOVED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="learning_group",
        target_id=str(group_id),
        metadata={"learner_id": str(learner_id), "assignments_cancelled": cancelled},
    )
    db.commit()
    return cancelled


def list_members(
    db: Session,
    *,
    group_id: uuid.UUID,
    include_removed: bool,
    limit: int,
    offset: int,
) -> tuple[list[MembershipView], int]:
    get_group(db, group_id)
    rows, total = repository.list_members(
        db,
        group_id=group_id,
        include_removed=include_removed,
        limit=limit,
        offset=offset,
    )
    return [MembershipView(membership=m, learner=learner) for m, learner in rows], total


__all__ = [
    "DuplicateGroupError",
    "DuplicateLearnerError",
    "DuplicateMembershipError",
    "GroupInactiveError",
    "GroupNotFoundError",
    "LearnerInactiveError",
    "LearnerNotFoundError",
    "MembershipNotFoundError",
    "MembershipView",
    "UserNotFoundError",
    "add_member",
    "create_group",
    "create_learner",
    "get_group",
    "get_learner",
    "group_member_count",
    "list_groups",
    "list_learners",
    "list_members",
    "remove_member",
    "update_group",
    "update_learner",
]
