"""Authentication provider boundary.

Authentication providers verify credentials supplied on the request and return
a verified :class:`AuthenticatedIdentity`, or ``None`` when no valid credential
is present. Token/session validation, issuer/audience/expiry checks, and
signature verification belong to a concrete provider implementation.

Providers selectable through ``AUTH_PROVIDER``:

- ``disabled`` (default): deny-by-default. Authenticates nobody, so every
  protected endpoint returns ``401``.
- ``development``: TEMPORARY local-development access mode. It grants a fixed
  local development identity without any sign-in. It is refused unless
  ``APP_ENV=development``. See ``app/security/development.py`` and
  ``docs/SECURITY.md``. It is not a login path and is not production-ready.

The concrete OIDC/SSO provider is intentionally not implemented yet: the
company identity provider is unconfirmed (see
``docs/adr/ADR-002-identity-provider.md``).
"""

from typing import Protocol

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.security.development import (
    DEVELOPMENT_APP_ENV,
    DEVELOPMENT_DISPLAY_NAME,
    DEVELOPMENT_EMAIL,
    DEVELOPMENT_IDENTITY_ID,
    DEVELOPMENT_PROVIDER,
    parse_development_roles,
)
from app.security.principal import AuthenticatedIdentity

DISABLED_PROVIDER = "disabled"
SUPPORTED_AUTH_PROVIDERS = frozenset({DISABLED_PROVIDER, DEVELOPMENT_PROVIDER})


class InvalidCredentialsError(Exception):
    """Raised by a provider when supplied credentials are malformed or invalid."""


class AuthenticationProvider(Protocol):
    name: str

    def authenticate(self, request: Request) -> AuthenticatedIdentity | None:
        """Return a verified identity, or ``None`` when unauthenticated."""
        ...


class DisabledAuthenticationProvider:
    """Deny-by-default provider used until an approved provider is configured."""

    name = DISABLED_PROVIDER

    def authenticate(self, request: Request) -> AuthenticatedIdentity | None:
        return None


class DevelopmentAuthenticationProvider:
    """TEMPORARY local-development access. Never selected outside development.

    Returns one fixed local identity for every request. It takes no client input,
    so request headers and bodies cannot change who the caller is.
    """

    name = DEVELOPMENT_PROVIDER

    def authenticate(self, request: Request) -> AuthenticatedIdentity | None:
        return AuthenticatedIdentity(
            external_identity_id=DEVELOPMENT_IDENTITY_ID,
            email=DEVELOPMENT_EMAIL,
            display_name=DEVELOPMENT_DISPLAY_NAME,
            development=True,
        )


def validate_auth_configuration(settings: Settings) -> None:
    """Fail fast at startup on an unsupported or unsafe authentication configuration."""
    provider = settings.auth_provider
    if provider not in SUPPORTED_AUTH_PROVIDERS:
        raise RuntimeError(
            f"AUTH_PROVIDER='{provider}' is not implemented yet. Supported values are "
            "'disabled' (default) and 'development' (local development only). A real "
            "identity provider requires an accepted ADR-002 and a reviewed implementation."
        )
    if provider == DEVELOPMENT_PROVIDER:
        if settings.app_env != DEVELOPMENT_APP_ENV:
            raise RuntimeError(
                "AUTH_PROVIDER=development grants access without sign-in and is only "
                f"permitted when APP_ENV={DEVELOPMENT_APP_ENV}. Current APP_ENV="
                f"'{settings.app_env}'. Refusing to start."
            )
        # Raises RuntimeError on unknown or forbidden roles.
        parse_development_roles(settings.dev_access_roles)


def get_authentication_provider(
    settings: Settings = Depends(get_settings),
) -> AuthenticationProvider:
    # Future providers are selected here (e.g. an OIDC provider). Only the
    # providers listed in SUPPORTED_AUTH_PROVIDERS can be selected.
    if settings.auth_provider == DEVELOPMENT_PROVIDER:
        return DevelopmentAuthenticationProvider()
    return DisabledAuthenticationProvider()
