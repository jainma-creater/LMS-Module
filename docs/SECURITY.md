# Security model

This document describes the authentication, authorization, auditing, and logging
model of the API as implemented for the Phase 1 auth foundation. It is a living
document; update it as the model changes.

## Authentication

Authentication is enforceably "closed" until an approved identity provider is
configured.

- Providers implement the `AuthenticationProvider` protocol
  (`app/security/providers.py`) and return a verified `AuthenticatedIdentity` or
  `None`/`InvalidCredentialsError`.
- `get_authentication_provider` is the single selection seam. Today the only
  default provider is `disabled` (`AUTH_PROVIDER=disabled`), which authenticates
  nobody. Every protected endpoint therefore returns `401`. The only other value,
  `development`, is the temporary local-only access mode described below.
- `validate_auth_configuration` runs at startup and refuses to boot for any
  unsupported `AUTH_PROVIDER` value, so an unimplemented provider cannot be
  half-enabled by configuration.
- **No client-supplied identity is trusted.** Headers such as `X-User-Id` or
  `X-Role` are ignored. Roles and permissions are always resolved server-side
  from the database for the verified identity.
- Token/session verification (issuer, audience, signature, expiry) is the
  provider's responsibility and is not yet implemented; see
  [ADR-002](adr/ADR-002-identity-provider.md).

### User provisioning

On first sight of a verified external identity, a local user is created with the
least-privilege `learner` role (JIT provisioning). Existing users are matched by
the stable `external_identity_id`. Non-active accounts are denied.

### Temporary development access mode (local development only)

Status: **TEMPORARY, for local development only. It is not authentication.** It
exists so the course-authoring workflow can be exercised before an approved
identity provider is configured (ADR-002). It must never be exposed to a public,
shared, or production network.

How it works:

- Selected only by `AUTH_PROVIDER=development`. The default remains `disabled`.
- Refused at startup unless `APP_ENV=development` exactly. Production, test,
  staging, empty, or differently cased values stop the API from starting. A test
  covers each case.
- Every request is treated as one fixed local identity
  (`local-development-user`). The identity is set on the server and ignores
  request headers and bodies.
- Its permissions come from `DEV_ACCESS_ROLES` (default `learning_admin`). They
  are applied to the in-request principal. Stored role assignments are not
  changed.
- `system_admin` cannot be granted. Role administration (`roles:assign`) and audit
  reads (`audit:read`) therefore stay denied and return `403`.
- Authorization checks still run on every route, and request validation is
  unchanged. Audit events are still written, attributed to the local development
  user.
- A warning is logged at startup (`development_access.enabled`) while the mode is
  active.

Known consequences:

- `GET /api/v1/me` shows the effective development roles, while
  `GET /api/v1/admin/users/{id}/roles` shows stored roles. They can differ.
- The mode does not verify any credential. Anyone who can reach the API can use
  it, so the API must be bound to loopback (`compose.yaml` does this).
- Removing the mode requires no code change: set `AUTH_PROVIDER` back to
  `disabled`. The real provider is added later in place of the development branch
  (see `app/security/providers.py`).

## Authorization

Authorization is deny-by-default and evaluated server-side on every protected
route via a reusable dependency (`require_permission`).

- Permissions are defined in code (`app/security/permissions.py`), not stored in
  the database, so adding a capability is an explicit, reviewable change.
- The role→permission map is explicit and least-privilege. There is **no
  wildcard administrator bypass**; `system_admin` holds an enumerated set.
- Unknown roles grant no permissions (deny by default).
- Authentication failures return `401`; authorization failures return `403`.
  Both use a consistent error envelope that includes a request ID.

Current permissions:

| Permission | Grants | Roles |
| --- | --- | --- |
| `profile:read` | Read own profile | learner, trainer, manager, learning_admin, system_admin, auditor |
| `roles:assign` | Grant/revoke user roles | system_admin |
| `audit:read` | Read audit events | system_admin, auditor |

Protected endpoints: `GET /api/v1/me` (authenticated); role administration under
`/api/v1/admin/users/{user_id}/roles` (`roles:assign`); audit access at
`GET /api/v1/admin/audit-events` (`audit:read`).

## Auditing

Security-relevant actions write an append-only `audit_events` row.

- Mutations write the audit row **in the same transaction** as the action, so the
  action and its audit record commit atomically; an audit write failure fails the
  operation rather than letting it succeed silently.
- Recorded today: successful authentication on first provisioning
  (`auth.succeeded`), failed authentication (`auth.failed`), role grant
  (`role.assigned`), role revocation (`role.revoked`), and audit access
  (`audit.read`).
- `actor_id` is nullable to represent unauthenticated events such as failed
  logins; it is set to `NULL` if an actor is later deleted.
- Audit metadata is sanitized for sensitive keys and bounded in size. **Never
  store secrets, tokens, or document contents in audit metadata.**

Event scope and retention are governed by ADR-007 (open); retention will be
finalized with compliance input.

## Logging

- Application logs are single-line JSON with `request_id` and `actor_id`
  correlation, emitted via `log_event`.
- Sensitive field names (passwords, tokens, cookies, secrets, keys/credentials)
  are redacted recursively before emission.
- Raw request bodies, credentials, tokens, cookies, and document contents are
  never logged.
- Failed audit writes are logged at `CRITICAL` so they are never silent.

## Response caching

Permission-gated read endpoints (for example the course catalog) return
`Cache-Control: private, max-age=…`. `private` forbids storage by shared or
intermediary caches, so one principal's response can never be served to another;
only the caller's own browser may reuse it briefly. Requests are still authorized
on every call, and no `Vary`-sensitive content is cached publicly.

## Reporting a problem

Security issues should be reported privately to the engineering/security owners
rather than filed publicly.
