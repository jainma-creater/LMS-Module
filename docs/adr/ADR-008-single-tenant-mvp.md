# ADR-008: Single-tenant data model for the MVP

- **Status:** Accepted
- **Date:** 2026-10-19
- **Owner:** Engineering (revisit if multi-tenancy is confirmed)

## Context

The specification warns against adding a tenant column without designing and
testing tenant isolation end-to-end. No multi-tenant requirement has been
confirmed for the MVP.

## Decision

Model the MVP as single-tenant: no `tenant_id` columns. Enforce isolation
through role-based access control and per-subject permissions (enrollment,
group membership, document permissions) only.

## Alternatives considered

- **Multi-tenant from day one:** rejected for now — significantly larger
  scope, requires isolation tests before any feature work, and is unconfirmed.

## Consequences

- Simpler schema and queries; fewer ways to leak data across tenants.
- If multi-tenancy is later required, it is a cross-cutting migration
  affecting every table, retrieval filter, and cache key. Revisit before
  Phase 3 (RAG) if the requirement emerges, since retrieval isolation is the
  hardest part to retrofit.
