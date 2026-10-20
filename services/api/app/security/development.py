"""TEMPORARY local-development access mode.

This module exists only so the course-authoring workflow can be exercised before
an approved identity provider is configured (see ADR-002). It is NOT
authentication and must never be enabled outside a developer's own machine.

Activation requires all of the following:

- ``AUTH_PROVIDER=development`` (explicit; the default is ``disabled``), and
- ``APP_ENV=development`` exactly. Production, test, staging, or any other value
  refuses to start (see ``validate_auth_configuration``).

When active, every request resolves to one fixed local development identity.
Its permissions come from ``DEV_ACCESS_ROLES`` (default ``learning_admin``), not
from stored role assignments, so the database is never changed to grant access.
``system_admin`` can never be granted by this mode, so role administration and
the audit read API stay closed. Audit events are still written for every
mutation, attributed to the local development user.
"""

from __future__ import annotations

import dataclasses

from app.security.permissions import Role, permissions_for_roles
from app.security.principal import Principal

DEVELOPMENT_PROVIDER = "development"
DEVELOPMENT_APP_ENV = "development"
DEVELOPMENT_IDENTITY_ID = "local-development-user"
DEVELOPMENT_EMAIL = "local-development@localhost"
DEVELOPMENT_DISPLAY_NAME = "Local development user"

# Roles that this mode must never grant. Role administration and audit access
# require a real, reviewed identity.
_FORBIDDEN_DEVELOPMENT_ROLES = frozenset({Role.SYSTEM_ADMIN})


def parse_development_roles(raw: str) -> frozenset[str]:
    """Parse ``DEV_ACCESS_ROLES`` into canonical role names, failing closed."""
    names = [part.strip() for part in raw.split(",") if part.strip()]
    if not names:
        raise RuntimeError("DEV_ACCESS_ROLES must name at least one role.")
    roles: set[str] = set()
    for name in names:
        try:
            role = Role(name)
        except ValueError:
            raise RuntimeError(f"DEV_ACCESS_ROLES contains unknown role '{name}'.") from None
        if role in _FORBIDDEN_DEVELOPMENT_ROLES:
            raise RuntimeError(f"Role '{name}' cannot be granted by development access.")
        roles.add(role.value)
    return frozenset(roles)


def apply_development_roles(principal: Principal, roles: frozenset[str]) -> Principal:
    """Return the principal with development-mode roles and permissions.

    The stored user row is untouched; only the in-request principal changes.
    """
    return dataclasses.replace(
        principal,
        roles=roles,
        permissions=frozenset(p.value for p in permissions_for_roles(roles)),
        development_access=True,
    )
