"""Reusable FastAPI dependencies for authentication and authorization.

- :func:`get_current_identity` authenticates the request at the provider boundary.
- :func:`get_current_principal` resolves the verified identity to a local principal.
- :func:`require_permission` enforces a specific permission (deny by default).

Authentication failures raise ``AuthenticationError`` (401). Authorization
failures raise ``AuthorizationError`` (403). Handlers are registered in
``app.main``.
"""

import logging
from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.logging import log_event
from app.db.session import get_db
from app.modules.audit import service as audit_service
from app.modules.audit.models import AuditOutcome
from app.modules.users import service as users_service
from app.security.development import apply_development_roles, parse_development_roles
from app.security.errors import AuthenticationError, AuthorizationError
from app.security.permissions import Permission
from app.security.principal import AuthenticatedIdentity, Principal
from app.security.providers import (
    AuthenticationProvider,
    InvalidCredentialsError,
    get_authentication_provider,
)

logger = logging.getLogger("ai_lms.security")


def _record_auth_failure(db: Session, reason: str) -> None:
    audit_service.record_event_best_effort(
        db,
        commit=True,
        action=audit_service.ACTION_AUTH_FAILED,
        outcome=AuditOutcome.FAILURE,
        error_code=reason,
    )
    log_event(
        "authentication.failed",
        level=logging.WARNING,
        outcome="failure",
        error_code=reason,
    )


def get_current_identity(
    request: Request,
    provider: AuthenticationProvider = Depends(get_authentication_provider),
    db: Session = Depends(get_db),
) -> AuthenticatedIdentity:
    """Return the verified identity or raise ``AuthenticationError``."""
    try:
        identity = provider.authenticate(request)
    except InvalidCredentialsError:
        _record_auth_failure(db, "invalid_credentials")
        raise AuthenticationError() from None

    if identity is None or not (identity.external_identity_id or "").strip():
        _record_auth_failure(db, "missing_identity")
        raise AuthenticationError()
    return identity


def get_current_principal(
    request: Request,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Principal:
    """Resolve the verified identity to a principal with roles and permissions."""
    principal = users_service.load_principal(db, identity)
    if identity.development:
        # Temporary local-development mode: permissions come from configuration,
        # not from stored roles. Only the development provider sets this flag.
        principal = apply_development_roles(
            principal, parse_development_roles(settings.dev_access_roles)
        )
    request.state.actor_id = str(principal.user_id)
    return principal


def require_permission(permission: Permission) -> Callable[..., Principal]:
    """Build a dependency that requires a specific permission."""

    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if not principal.has_permission(permission.value):
            log_event(
                "authorization.denied",
                level=logging.WARNING,
                outcome="failure",
                error_code="forbidden",
                actor_id=str(principal.user_id),
                permission=permission.value,
            )
            raise AuthorizationError()
        return principal

    return dependency
