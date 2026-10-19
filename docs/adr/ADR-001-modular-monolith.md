# ADR-001: Modular monolith as the initial deployment shape

- **Status:** Accepted
- **Date:** 2026-10-19
- **Owner:** Engineering (pending product/IT sign-off for production)

## Context

The product spans identity, course authoring, enrollment, progress,
assessment, content ingestion, AI retrieval, reporting, notifications, and
audit. The team and expected load do not yet justify distributed systems, and
the specification explicitly lists microservices, Kubernetes, and event
streaming as non-goals for the first release.

## Decision

Build a single deployable FastAPI application organized into modules with
explicit boundaries, sharing one PostgreSQL database. Keep the API and any
background worker in one repository, deployed as separate processes when jobs
exist. Keep AI provider calls behind interfaces so they can be replaced
without touching LMS logic.

## Alternatives considered

- **Microservices per module:** rejected — operational overhead without proven
  scale need; harder authorization consistency.
- **Single unstructured Django-style app:** rejected — spec wants explicit
  module boundaries and a typed API contract.
- **Serverless functions per endpoint:** rejected — complicates shared
  authorization and long-running ingestion jobs.

## Consequences

- Simpler local development, transactions can span modules, one migration
  history.
- Module boundaries are conventions, not enforced by the network; discipline
  and code review are required.
- Extraction to a service later is possible but not free; avoid leaking module
  internals across boundaries now.
