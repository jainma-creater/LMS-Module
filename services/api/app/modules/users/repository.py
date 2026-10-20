"""Database queries for the users module. Kept separate so authorization-relevant
queries are easy to inspect.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.users.models import Role, User, UserRole


def get_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def get_user_by_external_id(db: Session, external_identity_id: str) -> User | None:
    stmt = select(User).where(User.external_identity_id == external_identity_id)
    return db.execute(stmt).scalar_one_or_none()


def get_role_by_name(db: Session, name: str) -> Role | None:
    stmt = select(Role).where(Role.name == name)
    return db.execute(stmt).scalar_one_or_none()


def list_roles(db: Session) -> list[Role]:
    return list(db.execute(select(Role).order_by(Role.name)).scalars())


def list_role_names_for_user(db: Session, user_id: uuid.UUID) -> list[str]:
    stmt = (
        select(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
        .order_by(Role.name)
    )
    return list(db.execute(stmt).scalars())


def user_has_role(db: Session, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
    stmt = select(UserRole.id).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    return db.execute(stmt).scalar_one_or_none() is not None


def get_user_role(db: Session, user_id: uuid.UUID, role_id: uuid.UUID) -> UserRole | None:
    stmt = select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    return db.execute(stmt).scalar_one_or_none()
