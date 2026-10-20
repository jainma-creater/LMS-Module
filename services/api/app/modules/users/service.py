"""Business logic for identity resolution and role assignment.

Authorization-relevant logic lives here, not in route handlers. ``load_principal``
maps a verified external identity to a local principal, provisioning a
least-privilege user (default ``learner`` role) on first sight.
"""

import uuid

from sqlalchemy.orm import Session

from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditOutcome
from app.modules.users import repository
from app.modules.users.models import Role, User, UserRole, UserStatus
from app.security.errors import AuthorizationError
from app.security.permissions import Role as RoleName
from app.security.permissions import permissions_for_roles
from app.security.principal import AuthenticatedIdentity, Principal


class UserNotFoundError(Exception):
    """No user exists for the requested identifier."""


class RoleNotFoundError(Exception):
    """No role exists with the requested name."""


class RoleAlreadyAssignedError(Exception):
    """The user already holds the requested role."""


class RoleNotAssignedError(Exception):
    """The user does not hold the requested role."""


def ensure_roles(db: Session) -> None:
    """Idempotently insert the canonical roles. Safe to call repeatedly."""
    existing = {role.name for role in repository.list_roles(db)}
    added = False
    for role in RoleName:
        if role.value not in existing:
            db.add(Role(name=role.value))
            added = True
    if added:
        db.commit()


def load_principal(db: Session, identity: AuthenticatedIdentity) -> Principal:
    """Resolve a verified identity to a local principal.

    Provisions a new user with the least-privilege ``learner`` role when the
    external identity is seen for the first time. Raises ``AuthorizationError``
    if the account exists but is not active.
    """
    user = repository.get_user_by_external_id(db, identity.external_identity_id)
    if user is None:
        user = User(
            external_identity_id=identity.external_identity_id,
            email=identity.email,
            display_name=identity.display_name,
            status=UserStatus.ACTIVE,
        )
        db.add(user)
        db.flush()
        learner = repository.get_role_by_name(db, RoleName.LEARNER.value)
        if learner is not None:
            db.add(UserRole(user_id=user.id, role_id=learner.id))
        # First sighting of a verified identity: recorded as an authentication
        # success. Best-effort within this transaction; never blocks provisioning.
        audit_service.record_event_best_effort(
            db,
            action=audit_service.ACTION_AUTH_SUCCEEDED,
            outcome=AuditOutcome.SUCCESS,
            actor_id=user.id,
            target_type="user",
            target_id=str(user.id),
            metadata={"provisioned": True},
        )
        db.commit()
    elif user.status != UserStatus.ACTIVE:
        raise AuthorizationError("Account is not active.")

    role_names = frozenset(repository.list_role_names_for_user(db, user.id))
    permissions = frozenset(permission.value for permission in permissions_for_roles(role_names))
    return Principal(
        user_id=user.id,
        external_identity_id=user.external_identity_id,
        email=user.email,
        display_name=user.display_name,
        roles=role_names,
        permissions=permissions,
    )


def get_user(db: Session, user_id: uuid.UUID) -> User:
    user = repository.get_user_by_id(db, user_id)
    if user is None:
        raise UserNotFoundError(str(user_id))
    return user


def list_user_roles(db: Session, user_id: uuid.UUID) -> list[str]:
    return repository.list_role_names_for_user(db, user_id)


def assign_role(db: Session, *, actor: Principal, user_id: uuid.UUID, role_name: str) -> None:
    """Grant a role to a user and record an audit event atomically."""
    get_user(db, user_id)
    role = repository.get_role_by_name(db, role_name)
    if role is None:
        raise RoleNotFoundError(role_name)
    if repository.user_has_role(db, user_id, role.id):
        raise RoleAlreadyAssignedError(role_name)

    db.add(UserRole(user_id=user_id, role_id=role.id, assigned_by=actor.user_id))
    audit_service.record_event(
        db,
        action=audit_service.ACTION_ROLE_ASSIGNED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="user",
        target_id=str(user_id),
        metadata={"role": role_name},
    )
    db.commit()


def revoke_role(db: Session, *, actor: Principal, user_id: uuid.UUID, role_name: str) -> None:
    """Revoke a role from a user and record an audit event atomically."""
    get_user(db, user_id)
    role = repository.get_role_by_name(db, role_name)
    if role is None:
        raise RoleNotFoundError(role_name)
    user_role = repository.get_user_role(db, user_id, role.id)
    if user_role is None:
        raise RoleNotAssignedError(role_name)

    db.delete(user_role)
    audit_service.record_event(
        db,
        action=audit_service.ACTION_ROLE_REVOKED,
        outcome=AuditOutcome.SUCCESS,
        actor_id=actor.user_id,
        target_type="user",
        target_id=str(user_id),
        metadata={"role": role_name},
    )
    db.commit()
