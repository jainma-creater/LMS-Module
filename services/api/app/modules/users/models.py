"""Persistence models for identity and role assignment.

Roles are seeded rows; permission grants live in code
(``app.security.permissions``) to keep authorization reviewable.

Users are provisioned from a verified external identity (JIT). ``email`` and
``display_name`` are nullable because providers may not supply them, and email
uniqueness is enforced by a unique index (multiple NULLs are permitted).
"""

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppBase


class UserStatus:
    ACTIVE = "active"
    DISABLED = "disabled"
    INVITED = "invited"


class User(AppBase):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("external_identity_id", name="uq_users_external_identity_id"),
        UniqueConstraint("email", name="uq_users_email"),
    )

    external_identity_id: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=UserStatus.ACTIVE)


class Role(AppBase):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("name", name="uq_roles_name"),)

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class UserRole(AppBase):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_roles_user_role"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
