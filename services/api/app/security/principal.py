"""Core identity value objects.

``AuthenticatedIdentity`` is the verified, provider-supplied identity extracted
at the authentication boundary. ``Principal`` is the fully resolved application
identity: the local user plus the roles and permissions derived from the
database. Route handlers depend on ``Principal``, never on client-supplied
claims.
"""

import uuid
from dataclasses import dataclass, field


@dataclass(frozen=True)
class AuthenticatedIdentity:
    """Verified external identity. Produced by an ``AuthenticationProvider``."""

    external_identity_id: str
    email: str | None = None
    display_name: str | None = None
    # True only for the temporary local-development access mode (see
    # app.security.development). Never set by a real provider.
    development: bool = False


@dataclass(frozen=True)
class Principal:
    """Resolved application principal used for authorization decisions."""

    user_id: uuid.UUID
    external_identity_id: str
    email: str | None
    display_name: str | None
    roles: frozenset[str] = field(default_factory=frozenset)
    permissions: frozenset[str] = field(default_factory=frozenset)
    # True when roles/permissions came from the development access mode rather
    # than stored role assignments.
    development_access: bool = False

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions
