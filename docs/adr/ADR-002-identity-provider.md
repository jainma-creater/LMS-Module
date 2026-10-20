# ADR-002: Identity provider (SSO / OIDC / SAML)

- **Status:** Proposed — blocked pending confirmation of the company identity provider
- **Date:** 2026-10-19
- **Owner:** Engineering + IT/Security (joint; requires an org decision)

## Context

The platform must authenticate employees through the company's existing identity
provider. The specification does not name a provider, and the choice determines
the token format, claims, group/role mapping, and the session model. No SSO
credentials or endpoints may be invented.

To make progress without guessing, the authentication boundary has been built so
that the provider is the only undecided piece. Everything downstream of a
*verified* identity (provisioning, roles, permissions, audit, logging) is
implemented and provider-independent.

## Decision (interim)

1. **Provider is behind an interface.** `app/security/providers.py` defines an
   `AuthenticationProvider` protocol. `get_authentication_provider` is the single
   seam where a concrete provider is selected.
2. **Deny by default.** Until a concrete provider is configured, the
   `DisabledAuthenticationProvider` authenticates nobody, so every protected
   endpoint returns `401`. This is not a fake login path.
3. **Fail fast on misconfiguration.** `validate_auth_configuration` runs at
   startup and refuses to boot unless `AUTH_PROVIDER` is a supported value
   (currently only `disabled`).
4. **The provider owns credential verification.** Issuer/audience checks, token
   signature and expiry validation, and any session cookie handling belong to
   the concrete provider. It returns an `AuthenticatedIdentity` or raises
   `InvalidCredentialsError`; it never trusts client-supplied headers or roles.
5. **No client-supplied identity is ever trusted.** Roles and permissions are
   resolved server-side from the database for the verified identity.

## What is deliberately NOT decided here

- **Concrete provider** (e.g. Entra ID, Okta, Keycloak, Google Workspace).
- **Token/session model** — bearer access token vs. encrypted session cookie;
  token lifetimes, refresh, and logout behaviour.
- **Claim mapping** — which claim is the stable subject, and whether upstream
  groups map to local roles (and if so, how; see "Role mapping" below).
- **Credential/secrets handling** for the provider integration.

These require the company identity provider (ADR owner to be named) before a
provider implementation can be written and reviewed.

## Required inputs to close this ADR

1. Chosen provider and the protocol it exposes (OIDC authorization code + PKCE,
   SAML, etc.).
2. Issuer URL, allowed audiences, and how signing keys are obtained/rotated
   (e.g. OIDC discovery / JWKS).
3. The claim to use as the stable external subject (`external_identity_id`) and
   the claims for email and display name.
4. Whether group/role claims are authoritative. If yes, a mapping from
   upstream groups to local roles, and whether to provision on each login.
5. Session model preference (cookie vs. bearer) and cookie/CSRF policy if a
   browser session is used.

## Role mapping (to confirm)

If upstream groups drive roles, default to adding local roles and never removing
roles automatically unless explicitly agreed (to avoid surprise lockouts). The
local `learner` role remains the least-privilege default for newly seen
identities. `system_admin` is never granted automatically.

## Addendum: temporary development access mode

To let developers exercise the course-authoring workflow before this ADR closes,
an explicit local-only mode was added: `AUTH_PROVIDER=development`. It is refused
unless `APP_ENV=development`, grants a configured role set (`DEV_ACCESS_ROLES`,
never `system_admin`), and leaves stored roles unchanged. It is not an identity
provider and does not satisfy the requirements above. Full rules are in
`docs/SECURITY.md`. Remove it, or replace it with the real provider, when this ADR
is accepted.

## Consequences

- Protected endpoints are safe (closed) now; features that need data on behalf of
  a user stay unreachable until a provider is configured.
- Closing this ADR is a focused change: implement one provider against the
  existing interface, add configuration and tests, and update this record.
- Security review: token verification and session handling must be reviewed
  before any provider is enabled in a shared environment.
