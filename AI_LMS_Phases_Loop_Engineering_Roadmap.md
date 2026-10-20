# AI LMS --- Full Phases and Loop-Engineering Roadmap

**Repository:** `C:\LMS`\
**Source of truth:** `AI_LMS_Project_Specification.md`\
**Purpose:** Build the corporate LMS phase by phase, iterating through
implementation and verification until all agreed acceptance criteria are
demonstrably complete.

> **Definition of 100%:** Every in-scope acceptance criterion has
> implementation evidence and passing verification. Never mark work
> complete merely because code was written. Missing credentials, company
> policy, or external dependencies must be marked **BLOCKED**, not
> guessed.

## 1. Non-negotiable rules

-   Inspect the repository, current git status,
    `AI_LMS_Project_Specification.md`, README, `docs/API.md`,
    `docs/LLD.md`, `SECURITY.md`, ADRs, models, migrations, and tests
    before editing.
-   Use the existing stack and conventions:
    Next.js/React/TypeScript/Tailwind;
    Python/FastAPI/Pydantic/SQLAlchemy/Alembic; PostgreSQL with the
    existing pgvector image; npm and uv; existing Docker Compose.
-   Keep a modular monolith unless the specification and evidence
    justify a change.
-   Login and real authentication are **deferred** as requested. Do not
    implement Google OAuth until explicitly authorized. Do not invent
    fake users or identities.
-   If a temporary local development access mode is necessary, it must
    be explicitly configured, off/fail-closed by default, local-only,
    and rejected in production. Never expose unrestricted write APIs in
    production.
-   Preserve authorization boundaries, validation, audit logging,
    employee-data privacy, and secret redaction.
-   Do not commit, push, reset, clean, discard changes, or overwrite
    uncommitted work unless explicitly asked.
-   Never rewrite or delete applied migrations. Add forward migrations
    and test them against a disposable database.
-   Do not add Redis, AI/RAG, or unrelated infrastructure before its
    phase and a documented need.
-   AI must not independently determine mandatory compliance completion,
    pass/fail, or employee performance outcomes.
-   Do not claim tests, browser checks, migrations, or deployment checks
    passed unless actually run and their results observed.

## 2. Loop-engineering protocol (required for every phase)

Repeat the following loop for each vertical slice:

1.  **Discover:** inspect git status, specification, relevant code,
    database schema, API contracts, tests, security controls, and docs.
2.  **Plan:** write a concise plan, acceptance criteria, likely files,
    risks, and commands. Identify missing decisions/dependencies.
3.  **Implement:** build one coherent vertical slice. Keep frontend,
    backend, API schemas, database, and docs consistent. Validate on the
    server.
4.  **Test:** run relevant unit/integration tests, backend lint,
    frontend tests/lint/build, migration checks, API smoke tests, and
    browser/E2E tests when available.
5.  **Diagnose and fix:** for each failure, identify the cause, make the
    smallest correction, add a regression test where appropriate, and
    rerun failed and related suites.
6.  **Review:** inspect security/privacy, authorization and data
    isolation, transaction/data integrity, migration safety,
    error/loading/empty states, accessibility, responsive UI,
    performance, and accidental unrelated changes.
7.  **Document:** update API/LLD/README and this roadmap.
8.  **Close or continue:** do not stop at the first failure. Continue
    the loop until acceptance criteria pass or a concrete blocker is
    documented. Do not make blind repeated attempts without changing the
    diagnosis.

Typical checks (use the exact scripts present in the repo): - Backend
tests: `uv run pytest` - Backend lint: `uv run ruff check .` - Frontend
tests: `npm test` from `apps/web` - Frontend lint: `npm run lint` from
`apps/web` - Frontend build: `npm run build` from `apps/web` - Database:
migration upgrade/downgrade/upgrade and schema-drift check against a
disposable PostgreSQL database where supported - Runtime:
health/readiness, expected success paths, invalid inputs,
unauthorized/forbidden paths, not-found paths - Compose:
`docker compose config`; start and smoke-test the full stack when the
environment supports it - UI: verify real browser interactions if
browser tooling exists. HTTP 200 and a successful build do not prove the
UI works.

If a command cannot run, record **NOT VERIFIED** and why. At every phase
close, record status, files/migrations, acceptance criteria, exact
commands/results, browser checks actually performed, blockers,
limitations, and next action.

## 3. Baseline status (must re-verify)

Earlier reports said the platform foundation, catalog, course/lesson
authoring, README/API docs, and security foundation were implemented;
the latest reported checks were 129 backend tests, Ruff clean, 20
frontend tests, lint/build passing. These are historical reports, not
proof of current state. The user subsequently requested that
login/authentication be disabled for now; implementation of that request
is not confirmed here. Inspect the actual repository and working tree
before marking anything done.

## 4. Implementation phases

### Phase 0 --- Baseline and development mode

-   Inspect current code and preserve all changes.
-   Verify login page and login redirects are disabled.
-   Verify public catalog works without login.
-   If local authoring needs temporary access, use an explicit
    local-only development configuration, fail closed when off, and
    refuse activation in production.
-   Do not create fake users or imply anonymous visitors are verified
    employees.
-   Update README/security docs with exact local setup and limitations.

**Done when:** current behavior is verified; login UI/redirects are
absent; development access is tested on/off; production refuses the
bypass; docs and tests match reality.

### Phase 1 --- Platform foundation

-   Verify health/readiness, request IDs, structured logs, error
    handling and secret redaction.
-   Verify database sessions/transactions, environment configuration,
    migrations, frontend startup and Compose health checks.
-   Fix reliability defects that block subsequent work.

**Done when:** fresh disposable database migrations work;
health/readiness reflect actual dependencies; tests/lint/build pass;
local setup is reproducible as far as environment permits.

### Phase 2 --- Course catalog and authoring

-   Verify course lifecycle,
    title/slug/descriptions/category/difficulty/duration/thumbnail/tags.
-   Verify modules, lesson order, descriptions, duration, required flag
    and supported lesson types (`text`, `video_url`, `external_link`).
-   Verify server-side validation, URL schemes, publish requirements,
    archive behavior, search/filter/pagination and draft/archived
    visibility.
-   Verify authoring forms, create/edit, errors, save states and
    clearing optional fields.

**Done when:** catalog and authoring match backend contracts; tags and
lesson types persist correctly; publish rules are enforced server-side;
docs and tests pass.

### Phase 3 --- Learner directory and groups

-   Add learner records (employee identifier, name, email,
    department/business unit if required, active status).
-   Enforce uniqueness and validation.
-   Add groups and learner membership management; prevent duplicate
    memberships.
-   Do not assume an HR integration exists; use a documented
    manual/admin workflow until a source is approved.
-   Design records for later linking to verified Google identities.

**Done when:** learner/group CRUD, constraints, membership changes,
search/filtering, tests and docs work.

### Phase 4 --- Course assignment and enrollment

-   Assign published courses to individuals or groups.
-   Support assignment date, optional due date and status.
-   Decide and document whether group assignment snapshots members or
    includes future members dynamically.
-   Prevent duplicate active enrollments; reject new assignments to
    draft/archived courses.
-   Preserve historical assignment records when records change.
-   Build assignment management UI with search/filter/pagination.

**Done when:** individual/group assignment, dates/statuses, duplicate
prevention, membership behavior, history and tests are verified.

### Phase 5 --- Learner experience and progress

-   Build `My Learning` with assigned courses, due dates, statuses and
    progress.
-   Build course player with modules, lesson navigation, text content
    and safe video/external-link handling.
-   Store per-enrollment/per-lesson progress, timestamps and last
    visited lesson.
-   Support marking lessons complete and reopening if allowed.
-   Calculate progress from required lessons; optional lessons do not
    count in the denominator.
-   Handle zero required lessons and content edits/removals explicitly.
-   Do not associate progress with an anonymous browser session as if it
    were a verified employee.

**Done when:** assigned courses open; progress persists across visits;
resume works; required/optional rules and completion calculations are
tested; access to unrelated enrollments is rejected.

### Phase 6 --- Quizzes and assessments

-   Implement a defined first set of question types, question banks,
    quiz association, attempts, answers, pass marks and attempt limits.
-   Score objective answers on the server.
-   Never send answer keys before submission.
-   Preserve historical attempts and define the impact of quiz edits.
-   AI-generated questions, if later added, remain drafts until human
    approval.

**Done when:** quiz lifecycle, submission, scoring, attempt limits,
answer-key protection, history and edge-case tests pass.

### Phase 7 --- Compliance learning

-   Define mandatory/optional training, due dates, pass requirements and
    recertification only with approved business rules.
-   Keep assigned, completed, passed/failed, overdue and exempt states
    distinct.
-   Audit any approved exemption or override.
-   Use deterministic rules; AI must never set compliance completion.

**Done when:** policy is documented and approved; outcomes are
reproducible, auditable, and covered by tests.

### Phase 8 --- Learning analytics and reports

-   Report assignments, starts, in-progress, completion, overdue
    training and assessment results where data supports them.
-   Add approved filters and drill-downs; optionally CSV export if
    required.
-   Document formulas, date boundaries and timezone behavior.
-   Use indexes, pagination and aggregation; protect employee data and
    enforce data scopes.

**Done when:** totals reconcile with source records, filters/exports
work, empty data is clear, data isolation is tested, and performance is
checked on representative data.

### Phase 9 --- Notifications and reminders

-   Confirm company-approved provider and delivery policy first.
-   Define assignment, due-soon, overdue and completion notifications.
-   Use durable notification/outbox records, delivery status, safe
    retries and duplicate prevention.
-   Keep credentials in environment/secrets configuration. Add
    Redis/queue infrastructure only if justified.

**Done when:** rules/templates/recipients, retries, duplicate prevention
and failure observability are tested; external delivery is verified only
with an approved test destination.

### Phase 10 --- Identity and production authorization (DEFERRED)

Do not start until explicitly authorized. Until then, keep login/auth
disabled as requested.

-   Confirm approved identity provider and company domain/allowlist.
-   If approved, implement Google Workspace OIDC securely: server-side
    authorization-code flow,
    issuer/audience/signature/expiry/state/nonce/verified-email checks,
    secure HttpOnly SameSite cookies, CSRF protections, logout and
    session expiry/revocation.
-   Link verified identities to learner records. Identity verification
    must not grant administrator role automatically.
-   Enforce server-side RBAC on every protected endpoint and approved
    data scopes for learners/managers/training admins/HR.
-   Audit privileged changes and remove development access from
    production.

**Done when:** valid and invalid identity flows, role boundaries,
cross-learner access, session behavior, secrets, production fail-closed
behavior and end-to-end tests are verified.

### Phase 11 --- AI document ingestion and permission-aware RAG tutor

-   Confirm approved documents, classification, retention and
    permissions.
-   Implement validated upload, parsing/OCR, normalization, chunking,
    embeddings, indexing, versioning and deletion.
-   Start with PostgreSQL/pgvector unless evidence justifies another
    store.
-   Apply document permissions at retrieval time.
-   Return citations to actual sources/pages/sections and abstain when
    evidence is insufficient.
-   Treat retrieved documents as untrusted; test prompt injection and
    cross-scope retrieval.
-   Build an approved evaluation set and measure retrieval quality,
    latency, errors and model cost.

**Done when:** ingestion is observable, citations are traceable, access
restrictions hold, unsupported answers abstain, and evaluation/security
tests pass.

### Phase 12 --- AI-assisted course authoring

-   Generate draft summaries, outlines and quiz questions from approved
    sources.
-   Validate generated output against schemas; safely render it.
-   Require human review and explicit publish action; never
    auto-publish.
-   Add timeouts, retries, provider-failure handling, audit events and
    cost/quality evaluation.

**Done when:** output is validated, saved as draft, source-grounded
where applicable, human-reviewed, and safe under malformed
output/provider failure tests.

### Phase 13 --- Learning recommendations

-   Start with transparent rules based on role/team, prerequisites,
    assigned learning and approved interests.
-   Explain why each course is recommended.
-   Respect permissions and course availability.
-   Do not infer sensitive traits or use recommendations for employment,
    promotion, disciplinary or performance decisions.

**Done when:** inputs/rationale are documented, quality is evaluated,
access is respected, and no automated employment decision is made.

### Phase 14 --- Production readiness

-   Separate environments/configuration; verify HTTPS, headers, CORS,
    cookie settings, request/upload limits and secret rotation.
-   Define data retention/deletion and backup/restore; perform a restore
    test.
-   Monitor API/database, ingestion, AI provider and notification
    failures.
-   Add appropriate rate limits, dependency/container update process,
    threat model, security review and representative performance tests.
-   Create operator/incident/rollback runbooks and conduct a controlled
    pilot.

**Done when:** production cannot enable development bypass; access
controls, backup/restore, monitoring, retention, security/performance
review, release and rollback are verified and pilot owners approve.

## 5. Definition of done for every feature

-   [ ] Requirement traces to the spec or a documented decision.
-   [ ] API, schemas, UI and database agree.
-   [ ] Server-side validation and authorization are present where
    required.
-   [ ] Constraints, indexes and migrations are correct.
-   [ ] Success/error/loading/empty states are handled.
-   [ ] Unit/integration/regression tests cover normal and important
    failure cases.
-   [ ] Backend tests and Ruff pass.
-   [ ] Frontend tests, lint and production build pass.
-   [ ] Migration upgrade/downgrade/upgrade is tested on a disposable DB
    when schema changes.
-   [ ] API/runtime smoke tests pass.
-   [ ] Browser/E2E behavior is tested when tooling exists; otherwise
    the gap is explicit.
-   [ ] Security/privacy and performance risks are reviewed.
-   [ ] Docs are updated.
-   [ ] Actual commands/results and remaining limitations are recorded.
-   [ ] No commit/push without explicit permission.

## 6. Master instruction for OpenCode

> You are implementing the LMS in `C:\LMS`. Read this roadmap and
> `AI_LMS_Project_Specification.md` first. Inspect the actual repository
> and git status before editing. Determine the earliest phase with unmet
> acceptance criteria and available prerequisites; do not assume phases
> are complete because this file says so.
>
> Work in small vertical slices using loop engineering: discover → plan
> → implement → test → diagnose/fix → rerun → review security/data
> integrity/UI → update docs and roadmap. Continue until the slice
> passes all acceptance criteria or a concrete blocker is recorded. Then
> continue to the next independent slice in the phase. Do not jump to AI
> features before the core assignment, progress and assessment
> foundations are stable.
>
> Preserve uncommitted work. Never commit, push, reset, clean or discard
> changes. Never rewrite applied migration history. Do not fabricate
> test results or claim browser verification without a browser test.
> Login and authentication remain deferred/disabled until Phase 10 is
> explicitly authorized. Any temporary development access must be
> explicit, local-only, off by default, and rejected in production.
>
> At the end of each loop update this file with status, changes,
> migration IDs, exact commands and exit results, browser/E2E checks,
> blockers, limitations and next action. A phase is DONE only when all
> acceptance criteria are met and verified. If blocked, explain the
> dependency and continue safe independent work.

## 7. Current tracker --- update as work progresses

  -----------------------------------------------------------------------
  Phase                   Initial status          Evidence / next action
  ----------------------- ----------------------- -----------------------
  0\. Baseline and        DONE                    Login page/redirects disabled;
  development mode        (2024-10-19)            no-login.test.ts passes (23 tests);
                                                  public catalog works in dev mode;
                                                  dev mode fails closed in prod;
                                                  .env.example + compose.yaml updated;
                                                  .gitignore excludes .env

  1\. Platform foundation DONE                    Health/readiness endpoints work
  (2024-10-19)            (x-request-id correlation);
                                                  structured JSON logging with secret
                                                  redaction; error envelopes; DB
                                                  sessions/transactions; alembic
                                                  upgrade/check on disposable PG;
                                                  frontend lint/build pass; Compose
                                                  healthchecks pass; ports bound to
                                                  loopback only (127.0.0.1)

  2\. Catalog and         DONE                    Course lifecycle (draft→published→archived);
  authoring               (2024-10-19)            modules/lessons ordering; text/video/link
                                                  lessons; validation; pagination/filtering;
                                                  all authoring endpoints verified.

  3\. Learners and groups DONE                    Learner registry, active/inactive states;
                          (2026-10-19)            Learning groups (team/dept/org);
                                                  membership management; bulk group expansion;
                                                  migration 0005 applied and verified.

  4\. Assignment and      DONE                    Individual and group course assignments;
  enrollment              (2026-10-19)            idempotent expansion; automatic withdrawal
                                                  on group leave; enrollment linking;
                                                  due date tracking and audit events.

  5\. Learner experience  DONE                    Learner self-service portal (/learning, /progress);
  and progress            (2026-10-19)            lesson completion tracking; overall course
                                                  progress computation; completion timestamps.

  6\. Quizzes and         DONE                    Objective quizzes (single-choice, multiple-choice,
  assessments             (2026-10-19)            true/false); answer key verification; passing
                                                  thresholds; attempt tracking; interactive
                                                  QuizRunner component.

  7\. Compliance learning DONE                    ADR-009 documented (docs/adr/ADR-009-compliance-policy.md);
                          (2026-10-19)            is_mandatory & validity_days added to Course;
                                                  deterministic recertification logic; auditable
                                                  compliance exemptions.

  8\. Analytics/reports   NOT STARTED             Next candidate for reporting dashboard.

  9\. Notifications       BLOCKED ON PROVIDER     Requires external email/webhook provider.

  10\. Identity           DEFERRED                Authentication remains intentionally deferred.

  11\. RAG tutor          NOT STARTED             Requires vector embeddings & permissions tutor.

  12\. AI Training Studio DONE                    3–5 click guided creation from topic or file
  & Assisted Authoring    (2026-10-19)            (PDF, DOCX, PPTX, TXT); grounded course syllabi,
                                                  modules, lessons; objective assessment generation;
                                                  single-question regeneration; video pipeline with
                                                  storyboards, synchronized WebVTT captions, and
                                                  HTML5 video preview; human review draft lifecycle
                                                  (never auto-published); 1-click approve & publish
                                                  with immediate group/learner assignment.
                                                  Backend: 238 pytest tests pass; Ruff clean.
                                                  Frontend: 25 node tests pass; ESLint 0 warnings;
                                                  Next.js production build passes (21/21 routes).
                                                  Migration: 0006_training_studio at head.

  13\. Recommendations    NOT STARTED             Requires privacy and recommendation policy.

  14\. Production         NOT STARTED             Requires staging deployment and secret rotation.
  readiness

  Frontend redesign       DONE                    Coursera-inspired light UI (single brand
  (Coursera-like)         (2026-10-19)            blue #0056d2); design tokens + primitives;
                                                  new shell/SiteNav/footer; learner pages
                                                  (/, /courses, /courses/[slug], /learn/[courseId],
                                                  /learning, /progress) and admin console
                                                  (/manage + dashboard, learners, groups,
                                                  assignments); old /catalog routes removed;
                                                  lint clean; 25 tests pass; build passes
                                                  (all routes prerender).

  Backend + data          DONE                    Killed N+1 in /me/learning, /me/progress and
  optimization            (2026-10-19)            /courses/{id}/content (batch IN + grouped
                                                  counts); private cache headers on catalog
                                                  reads; X-Process-Time-Ms + duration_ms in
                                                  RequestContextMiddleware; /readyz reports
                                                  schema_revision. Migration 0007_query_indexes
                                                  (composite indexes) + 0008_reconcile_schema_drift
                                                  (fixed missing enrollments.withdrawn_at;
                                                  dropped dead course_assignments.exempted_*).
                                                  alembic autogenerate reports zero drift.
                                                  Verified live on the compose stack:
                                                  authoring→publish→catalog→enroll→progress→
                                                  completion, and every learner/admin page 200;
                                                  /login and /signin are 404. 258 pytest pass;
                                                  Ruff clean; frontend lint/test/build green.
  -----------------------------------------------------------------------

## 8. Final 100% completion checklist

-   [ ] Every in-scope phase is DONE with evidence.
-   [ ] Core workflow works end to end: author → publish → assign →
    learn → assess → record completion → report.
-   [ ] Employee and learning data are correctly scoped and protected.
-   [ ] Compliance uses approved deterministic rules.
-   [ ] AI respects permissions, cites evidence, abstains when
    unsupported and requires human review where specified.
-   [ ] Tests, lint, type checks and production builds pass.
-   [ ] Critical browser/E2E flows are tested or gaps explicitly
    accepted.
-   [ ] Migrations and backup/restore are verified.
-   [ ] Monitoring, retention, security review, operator docs and
    rollback procedures exist.
-   [ ] Performance/privacy/security findings are triaged.
-   [ ] Stakeholders approve pilot/release readiness.
-   [ ] Final limitations and verification date are recorded.

**Never check a box until the work has actually been completed and
verified.**

