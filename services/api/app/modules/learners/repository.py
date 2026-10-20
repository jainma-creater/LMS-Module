"""Database queries for learner records and learning groups."""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.learners.models import (
    Learner,
    LearnerStatus,
    LearningGroup,
    LearningGroupMember,
)


def _like(term: str) -> str:
    return f"%{term}%"


# --------------------------------------------------------------------------- #
# Learners
# --------------------------------------------------------------------------- #
def get_learner(db: Session, learner_id: uuid.UUID) -> Learner | None:
    return db.get(Learner, learner_id)


def get_learner_by_employee_id(db: Session, employee_id: str) -> Learner | None:
    stmt = select(Learner).where(Learner.employee_id == employee_id)
    return db.execute(stmt).scalar_one_or_none()


def get_learner_by_email(db: Session, email: str) -> Learner | None:
    return db.execute(select(Learner).where(Learner.email == email)).scalar_one_or_none()


def get_learner_by_user_id(db: Session, user_id: uuid.UUID) -> Learner | None:
    return db.execute(select(Learner).where(Learner.user_id == user_id)).scalar_one_or_none()


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
    conditions = []
    if search:
        pattern = _like(search.strip())
        conditions.append(
            or_(
                Learner.first_name.ilike(pattern),
                Learner.last_name.ilike(pattern),
                Learner.employee_id.ilike(pattern),
                Learner.email.ilike(pattern),
            )
        )
    if status:
        conditions.append(Learner.status == status)
    if department:
        conditions.append(Learner.department == department)
    if business_unit:
        conditions.append(Learner.business_unit == business_unit)

    stmt = select(Learner)
    count_stmt = select(func.count(Learner.id))
    if conditions:
        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)
    stmt = (
        stmt.order_by(Learner.last_name, Learner.first_name, Learner.id).limit(limit).offset(offset)
    )
    items = list(db.execute(stmt).scalars())
    total = db.execute(count_stmt).scalar_one()
    return items, total


def list_active_learners_for_selection(db: Session, limit: int = 500) -> list[Learner]:
    stmt = (
        select(Learner)
        .where(Learner.status == LearnerStatus.ACTIVE)
        .order_by(Learner.last_name, Learner.first_name, Learner.id)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars())


# --------------------------------------------------------------------------- #
# Learning groups
# --------------------------------------------------------------------------- #
def get_group(db: Session, group_id: uuid.UUID) -> LearningGroup | None:
    return db.get(LearningGroup, group_id)


def get_group_by_name(db: Session, name: str) -> LearningGroup | None:
    return db.execute(select(LearningGroup).where(LearningGroup.name == name)).scalar_one_or_none()


def count_active_members(db: Session, group_id: uuid.UUID) -> int:
    stmt = select(func.count(LearningGroupMember.id)).where(
        LearningGroupMember.group_id == group_id,
        LearningGroupMember.removed_at.is_(None),
    )
    return db.execute(stmt).scalar_one()


def active_member_counts(db: Session, group_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not group_ids:
        return {}
    stmt = (
        select(LearningGroupMember.group_id, func.count(LearningGroupMember.id))
        .where(
            LearningGroupMember.group_id.in_(group_ids),
            LearningGroupMember.removed_at.is_(None),
        )
        .group_by(LearningGroupMember.group_id)
    )
    return {group_id: count for group_id, count in db.execute(stmt).all()}


def list_groups(
    db: Session,
    *,
    search: str | None,
    status: str | None,
    kind: str | None,
    limit: int,
    offset: int,
) -> tuple[list[LearningGroup], int]:
    conditions = []
    if search:
        conditions.append(LearningGroup.name.ilike(_like(search.strip())))
    if status:
        conditions.append(LearningGroup.status == status)
    if kind:
        conditions.append(LearningGroup.kind == kind)

    stmt = select(LearningGroup)
    count_stmt = select(func.count(LearningGroup.id))
    if conditions:
        stmt = stmt.where(*conditions)
        count_stmt = count_stmt.where(*conditions)
    stmt = stmt.order_by(LearningGroup.name, LearningGroup.id).limit(limit).offset(offset)
    items = list(db.execute(stmt).scalars())
    total = db.execute(count_stmt).scalar_one()
    return items, total


def get_active_membership(
    db: Session, group_id: uuid.UUID, learner_id: uuid.UUID
) -> LearningGroupMember | None:
    stmt = select(LearningGroupMember).where(
        LearningGroupMember.group_id == group_id,
        LearningGroupMember.learner_id == learner_id,
        LearningGroupMember.removed_at.is_(None),
    )
    return db.execute(stmt).scalar_one_or_none()


def list_members(
    db: Session,
    *,
    group_id: uuid.UUID,
    include_removed: bool,
    limit: int,
    offset: int,
) -> tuple[list[tuple[LearningGroupMember, Learner]], int]:
    conditions = [LearningGroupMember.group_id == group_id]
    if not include_removed:
        conditions.append(LearningGroupMember.removed_at.is_(None))
    stmt = (
        select(LearningGroupMember, Learner)
        .join(Learner, Learner.id == LearningGroupMember.learner_id)
        .where(*conditions)
        .order_by(Learner.employee_id, LearningGroupMember.id)
        .limit(limit)
        .offset(offset)
    )
    count_stmt = select(func.count(LearningGroupMember.id)).where(*conditions)
    rows = [(member, learner) for member, learner in db.execute(stmt).all()]
    total = db.execute(count_stmt).scalar_one()
    return rows, total


def list_active_member_learners(db: Session, group_id: uuid.UUID) -> list[Learner]:
    stmt = (
        select(Learner)
        .join(LearningGroupMember, LearningGroupMember.learner_id == Learner.id)
        .where(
            LearningGroupMember.group_id == group_id,
            LearningGroupMember.removed_at.is_(None),
        )
        .order_by(Learner.employee_id, Learner.id)
    )
    return list(db.execute(stmt).scalars())
