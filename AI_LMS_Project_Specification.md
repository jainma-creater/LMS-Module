# AI-Powered Corporate Learning Management System (AI LMS)

**Project specification for implementation with OpenCode**\
**Version:** 1.0\
**Date:** 2026-10-19\
**Status:** Draft for technical review

------------------------------------------------------------------------

## 1. Executive summary

Build an enterprise Learning Management System (LMS) for employees,
trainers, managers, and learning administrators. The product combines
conventional LMS workflows with an AI learning assistant grounded in
company-approved training material.

### Recommended approach

Build a **modular monolith** first. Keep the core LMS as a conventional,
deterministic application and implement AI capabilities as a separately
testable module behind provider interfaces. Do not start with
microservices or train a foundation model.

### Product goals

1.  Let administrators create and assign courses and learning paths.
2.  Let employees consume lessons, take assessments, and track progress.
3.  Let managers see team completion and overdue training.
4.  Let authorized employees ask questions about approved course
    documents and receive source citations.
5.  Help content authors generate draft summaries and quiz questions,
    with human review before publishing.
6.  Keep company content private and enforce access control consistently
    across normal LMS APIs and AI retrieval.

### Non-goals for the first release

-   Training a foundation model from scratch.
-   Building a public MOOC marketplace.
-   Fully autonomous grading of high-stakes assessments.
-   Replacing the HR system as the system of record for employee
    identity.
-   Complex microservices, Kubernetes, or event streaming before actual
    scale requires them.

------------------------------------------------------------------------

## 2. Assumptions and decisions to confirm

This document assumes a corporate employee-learning use case,
potentially including mandatory compliance training. Confirm these items
with the product owner and company IT/security before production:

-   Expected employee count and peak concurrent users.
-   Required identity provider: Microsoft Entra ID, Google Workspace,
    another SAML/OIDC provider, or local accounts for development only.
-   Approved cloud/on-premises hosting and data residency requirements.
-   Whether training material contains confidential, regulated, or
    personally identifiable information.
-   Video hosting, storage, email, HRMS, and reporting integrations.
-   Whether certificates, expiry dates, reminders, and compliance
    evidence are required.
-   Approved AI vendors and whether company content may be sent to a
    third-party model API.
-   Retention, deletion, audit, backup, and incident-response
    requirements.

**Security gate:** do not upload internal company documents to a public
AI service until the company has approved the provider, terms, data
handling, and retention configuration.

------------------------------------------------------------------------

## 3. User roles and permissions

  -----------------------------------------------------------------------
  Role                                Main permissions
  ----------------------------------- -----------------------------------
  Learner / Employee                  View assigned courses, study
                                      lessons, take quizzes, view own
                                      progress, ask questions about
                                      content they can access

  Trainer / Content Author            Create and edit assigned courses,
                                      upload material, draft summaries
                                      and quizzes, submit content for
                                      review

  Manager                             View permitted team learning status
                                      and reports; cannot see unrelated
                                      employees' private data

  Learning Administrator              Manage course catalog, enrollments,
                                      assignments, learning paths,
                                      completion rules, and reports

  System Administrator                Configure integrations, roles,
                                      tenant settings, security settings,
                                      and operational health

  Auditor / Compliance Reviewer       Read-only access to specifically
                                      authorized completion evidence and
                                      audit records
  -----------------------------------------------------------------------

Use deny-by-default authorization. Hiding a button in the UI is not
access control; every API and retrieval operation must check permissions
server-side.

------------------------------------------------------------------------

## 4. Functional requirements

### 4.1 Core LMS --- MVP

-   Authentication and session management.
-   Employee profile and role assignment.
-   Course catalog with search, category, tags, status, and version.
-   Course structure: course → modules/sections → lessons.
-   Lesson content: text, links, approved documents, and video links.
-   Course assignment/enrollment to individuals or groups.
-   Lesson completion and resumable progress.
-   Quizzes with multiple-choice questions, attempt limits, scoring, and
    pass thresholds.
-   Course completion rules and completion history.
-   Admin dashboard for assignments, completion, overdue training, and
    basic exports.
-   Notifications/reminders through an approved email provider.
-   Audit records for security-sensitive and compliance-relevant
    actions.

### 4.2 AI features --- staged rollout

**AI-1: Course document assistant** - Answer questions using only
authorized, indexed training sources where possible. - Display source
title and page/section/chunk citation. - Say when the evidence is
insufficient; do not invent policy answers. - Respect course enrollment,
document permissions, and document version. - Record safe operational
metadata, not unnecessary sensitive prompt contents.

**AI-2: Learning-content assistance** - Generate draft lesson
summaries. - Generate draft quiz questions and explanations from
selected sources. - Return structured output validated against a
schema. - Require author review and approval before publishing.

**AI-3: Personalization** - Recommend the next course based on role,
assigned learning path, completion status, and explicit learning
goals. - Explain why a course was recommended. - Do not infer sensitive
employee traits or make employment decisions from AI outputs.

### 4.3 Later enhancements

-   SCORM/xAPI support if required by existing training packages.
-   HRMS synchronization and organizational hierarchy.
-   SSO and automated user provisioning.
-   Multi-language content and assistant responses.
-   Advanced analytics, cohort comparisons, and learning effectiveness.
-   Video transcription and searchable captions.
-   Accessibility checks and mobile-responsive learner experience.

------------------------------------------------------------------------

## 5. Recommended technology stack

  -----------------------------------------------------------------------
  Layer                   Recommendation          Reason / notes
  ----------------------- ----------------------- -----------------------
  Frontend                Next.js, React,         Product UI, routing,
                          TypeScript              dashboards,
                                                  server/client rendering
                                                  where useful

  UI                      Tailwind CSS +          Fast, consistent
                          shadcn/ui               internal product UI

  API                     Python + FastAPI +      Typed API contracts and
                          Pydantic                straightforward
                                                  integration with AI
                                                  tooling

  ORM / migrations        SQLAlchemy 2.x +        Explicit data models
                          Alembic                 and controlled schema
                                                  migrations

  Primary database        PostgreSQL              Users, courses,
                                                  assignments, progress,
                                                  assessments, audit
                                                  metadata

  Vector retrieval        PostgreSQL + pgvector   Keep vector data near
                          initially               source metadata and
                                                  permissions; evaluate a
                                                  dedicated vector DB
                                                  only if justified

  Cache / jobs            Redis + Celery or RQ    Background document
                                                  ingestion,
                                                  notifications, and
                                                  longer AI tasks

  File storage            Company-approved        Store originals and
                          S3-compatible object    processed artifacts
                          storage or cloud object privately; keep file
                          storage                 bytes out of the
                                                  relational database

  Document parsing        PyMuPDF / pypdf,        Extract supported file
                          python-docx, openpyxl   types; inspect parser
                          as appropriate          security and resource
                                                  limits

  AI orchestration        Small provider adapter; Avoid making the
                          optionally LangChain or application dependent
                          LlamaIndex for selected on a framework-specific
                          components              abstraction

  Embeddings              An approved embedding   Select based on
                          API or a vetted local   language, quality,
                          embedding model         privacy, latency, and
                                                  cost

  LLM                     Approved hosted model   Use separate
                          API or an approved      configurable choices
                          self-hosted model       for generation and
                                                  embeddings

  Authentication          OIDC/SAML via company   Prefer enterprise SSO
                          identity provider;      over custom password
                          secure server-side      handling
                          sessions                

  Testing                 pytest, HTTPX, frontend Test API behavior,
                          unit/component tests,   permissions, UI flows,
                          Playwright              and AI retrieval
                                                  quality

  Observability           Structured logs,        Redact secrets and
                          metrics, traces, error  sensitive
                          reporting approved by   employee/document
                          IT                      content

  Deployment              Docker;                 Start with a simple
                          company-approved cloud  deployable topology;
                          or internal platform    expand based on load
                                                  and IT requirements

  CI/CD                   Company-approved        Tests, dependency
                          GitHub/GitLab pipeline  checks, secret
                                                  scanning, migrations
                                                  and deployment
                                                  approvals
  -----------------------------------------------------------------------

### Important implementation guidance

-   Pin dependency versions and commit lockfiles.
-   Use supported versions at implementation time; do not blindly copy
    version numbers from an old repository.
-   Use asynchronous FastAPI endpoints only where the underlying I/O
    libraries and workload benefit from them.
-   Use background jobs for parsing, chunking, embedding, bulk
    notifications, and long AI generations.
-   Keep business rules in the backend, not only in React components.
-   Use a single source of truth for authorization and course completion
    logic.

------------------------------------------------------------------------

## 6. AI model strategy

Do not choose a model solely from a benchmark or brand name. Evaluate
approved candidates using representative internal training material and
a fixed test set.

### 6.1 Model responsibilities

  -----------------------------------------------------------------------
  Task                    Model/component         Selection criteria
  ----------------------- ----------------------- -----------------------
  Q&A response            General-purpose         Grounded accuracy,
                          instruction-following   refusal behavior,
                          LLM                     latency, cost, approved
                                                  data handling

  Embeddings              Text embedding model    Retrieval recall,
                                                  multilingual quality,
                                                  vector dimensions,
                                                  privacy, cost

  Reranking (optional)    Cross-encoder or        Better ordering of
                          reranking API           retrieved passages;
                                                  latency and cost

  Quiz / summary          Same LLM initially,     Factuality, valid JSON,
  generation              with task-specific      coverage of source
                          prompts and schemas     material

  Document extraction     Parsers/OCR, not        Layout support, OCR
                          necessarily an LLM      quality, security,
                                                  repeatability

  Speech transcription    Approved speech-to-text Language/accent
  (later)                 model                   quality, consent,
                                                  retention, price
  -----------------------------------------------------------------------

### 6.2 Hosted versus local

**Hosted API** - Usually the quickest MVP path and often offers strong
quality. - Requires company approval for data handling, retention,
region, and contractual terms. - Add timeouts, retry limits, quotas,
cost monitoring, and provider abstraction.

**Self-hosted model** - Can give more control over deployment and data
flow. - Requires GPU/CPU capacity, model-serving expertise, security
patching, scaling, and evaluation. - May have weaker quality or higher
operational cost for a small team. - Do not assume local automatically
means secure; access controls, logs, storage, and model artifacts also
need protection.

### 6.3 Model selection process

1.  Build a test set of real, approved training questions and expected
    source passages.
2.  Include normal questions, ambiguous questions, missing-answer
    questions, conflicting document versions, and prompt-injection
    attempts.
3.  Evaluate retrieval separately from answer generation.
4.  Score factual correctness, citation correctness, refusal when
    unsupported, latency, and cost.
5.  Select the least expensive approved option that meets the quality
    and security threshold.
6.  Keep model name, endpoint, embedding model, chunking settings, and
    prompt version in configuration.
7.  Re-run the evaluation suite when any model, prompt, parser, or
    retrieval setting changes.

### 6.4 RAG design

RAG = Retrieval-Augmented Generation. It retrieves relevant approved
passages and supplies them to the model as evidence.

**Ingestion pipeline** 1. Authorized author uploads a file. 2. Validate
extension, MIME type, size, and file signature; scan it for malware. 3.
Store original file in private object storage. 4. Extract text and
metadata; preserve page/section references. 5. Split text into
overlapping, semantically useful chunks. 6. Generate embeddings. 7.
Store chunk text or protected content reference, vector, document
version, source location, and access metadata. 8. Mark the document
indexed only after the pipeline completes successfully.

**Question pipeline** 1. Authenticate the employee. 2. Resolve their
tenant, role, course enrollment, and document permissions. 3. Embed the
question. 4. Retrieve only eligible chunks, applying permission filters
before content is exposed to the LLM. 5. Optionally rerank the retrieved
candidates. 6. Generate a concise answer using the retrieved evidence.
7. Validate output and citations; return source links/page references.
8. If evidence is weak or absent, explain that the available training
material does not answer the question. 9. Log request ID, timing,
model/version, retrieval IDs, token/cost metrics, and outcome as
permitted by company policy.

**Critical:** do not retrieve from all company documents and rely on the
LLM to hide unauthorized information. Enforce access control in the
retrieval query and test it with cross-role and cross-course cases.

### 6.5 AI safety and quality requirements

-   Treat uploaded documents and retrieved text as untrusted data, not
    instructions to the assistant.
-   Do not expose system prompts, credentials, hidden context, or other
    users' content.
-   Defend against indirect prompt injection embedded in documents.
-   Do not let an AI tool execute arbitrary SQL, shell commands, or
    unrestricted URLs.
-   Validate structured model output with Pydantic and reject invalid
    results.
-   Use a fixed, versioned system prompt and regression tests.
-   Show citations that map to actual retrieved chunks; never fabricate
    page numbers or sources.
-   Separate AI-generated drafts from published course content.
-   Provide rate limits, request timeouts, token limits, and
    per-user/per-tenant quotas.
-   Define human review and escalation for compliance/policy answers.

------------------------------------------------------------------------

## 7. High-Level Design (HLD)

### 7.1 Logical architecture

``` mermaid
flowchart TB
    U[Learner / Trainer / Manager / Admin] --> WEB[Next.js Web App]
    WEB --> API[FastAPI API Layer]
    API --> AUTH[OIDC / SSO Provider]
    API --> PG[(PostgreSQL + pgvector)]
    API --> REDIS[(Redis)]
    API --> OBJ[Private Object Storage]
    API --> AI[AI Service / Provider Adapter]
    API --> JOBS[Background Worker]
    REDIS --> JOBS
    JOBS --> OBJ
    JOBS --> PARSE[Parse / Chunk / Embed]
    PARSE --> PG
    AI --> LLM[Approved LLM API or Model Server]
    AI --> EMB[Approved Embedding Model]
    JOBS --> EMAIL[Approved Email Provider]
```

This is a logical view, not a requirement to deploy each box as a
separate service. For the MVP, keep the API and worker in one repository
and deploy them as separate processes/containers.

### 7.2 Application modules

1.  **Identity and access:** user profile, role, group, SSO integration,
    session.
2.  **Course catalog:** courses, modules, lessons, versioning,
    publishing.
3.  **Enrollment and assignment:** users/groups assigned to courses, due
    dates.
4.  **Progress and assessment:** lesson progress, quiz attempts,
    scoring, completion.
5.  **Content ingestion:** upload, validation, parsing, chunking,
    indexing state.
6.  **AI learning assistant:** retrieval, citations, response
    generation, feedback.
7.  **Authoring assistance:** summaries and quiz drafts with approval
    workflow.
8.  **Reporting:** completion, overdue assignments, course engagement.
9.  **Notifications:** due-date reminders and completion messages.
10. **Audit and administration:** access-sensitive events,
    configuration, operations.

### 7.3 Key architectural choices

-   **Modular monolith:** modules have explicit boundaries but share one
    deployable API and relational database initially.
-   **PostgreSQL first:** use relational tables for authoritative LMS
    state. Use pgvector for initial retrieval if approved and
    operationally suitable.
-   **Async work:** document indexing and other long operations must not
    block normal API requests.
-   **Private object storage:** store files privately; issue
    short-lived, authorized download URLs only when needed.
-   **Provider abstraction:** AI provider code should be replaceable
    without rewriting course or enrollment logic.
-   **Versioning:** retain document/course versions and link citations
    to the exact source version used.
-   **Observability:** correlation/request IDs across API, worker,
    database, and AI calls.

------------------------------------------------------------------------

## 8. Low-Level Design (LLD)

### 8.1 Suggested repository layout

``` text
ai-lms/
├── apps/
│   └── web/                       # Next.js + TypeScript
├── services/
│   ├── api/                       # FastAPI application
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── core/              # config, auth, logging, errors
│   │   │   ├── db/                # session, base, migrations integration
│   │   │   ├── modules/
│   │   │   │   ├── users/
│   │   │   │   ├── courses/
│   │   │   │   ├── enrollments/
│   │   │   │   ├── progress/
│   │   │   │   ├── assessments/
│   │   │   │   ├── documents/
│   │   │   │   ├── ai_tutor/
│   │   │   │   ├── reports/
│   │   │   │   └── audit/
│   │   │   └── shared/
│   │   ├── tests/
│   │   └── pyproject.toml
│   └── worker/                    # ingestion and notification jobs
├── packages/
│   └── api-client/                # generated/shared TypeScript API types if useful
├── infra/
│   ├── docker/
│   └── deployment/
├── docs/
│   ├── HLD.md
│   ├── LLD.md
│   ├── API.md
│   ├── SECURITY.md
│   └── ADR/
├── compose.yaml                   # local development only
├── .env.example                   # placeholders only; never real secrets
└── README.md
```

Keep this structure pragmatic. Do not create empty packages or
abstractions before they are needed.

### 8.2 Backend module layering

Within each module, use a simple separation:

-   `router.py`: HTTP request/response contracts and dependency wiring.
-   `schemas.py`: Pydantic request and response schemas.
-   `service.py`: business rules and orchestration.
-   `repository.py`: database queries where this separation is useful.
-   `models.py`: SQLAlchemy persistence models.
-   `tasks.py`: background job definitions if applicable.
-   `tests/`: unit and integration tests.

Avoid putting business logic directly into route handlers. Avoid a
generic repository framework that hides SQL and makes authorization
difficult to inspect.

### 8.3 Initial data model

Use UUIDs for externally exposed identifiers. Add `created_at`,
`updated_at`, and appropriate foreign keys to relevant tables. Add
tenant identifiers if multi-tenancy is a real requirement; do not add a
tenant column without designing and testing tenant isolation end-to-end.

**Core entities**

  -----------------------------------------------------------------------
  Entity                              Important fields / relationships
  ----------------------------------- -----------------------------------
  `users`                             id, external_identity_id, email,
                                      display_name, status

  `roles`                             id, name

  `user_roles`                        user_id, role_id, scope if needed

  `groups`                            id, name, organizational scope

  `group_memberships`                 group_id, user_id

  `courses`                           id, title, description, status,
                                      owner_id, version

  `modules`                           id, course_id, title, sort_order

  `lessons`                           id, module_id, title, content_type,
                                      content_ref, sort_order

  `enrollments`                       id, user_id, course_id,
                                      assigned_by, due_at, status

  `lesson_progress`                   id, user_id, lesson_id, status,
                                      completed_at, last_position

  `quizzes`                           id, course_id or lesson_id,
                                      pass_score, attempt_limit

  `questions`                         id, quiz_id, type, prompt,
                                      options_json, answer_key,
                                      explanation

  `quiz_attempts`                     id, quiz_id, user_id, started_at,
                                      submitted_at, score, status

  `quiz_responses`                    id, attempt_id, question_id,
                                      response_json, is_correct

  `course_completions`                id, user_id, course_id,
                                      completed_at,
                                      completion_rule_version

  `documents`                         id, title, object_key, owner_id,
                                      status, version, checksum

  `document_permissions`              document_id, subject_type,
                                      subject_id, permission

  `document_chunks`                   id, document_id, version,
                                      chunk_index, text/content_ref,
                                      embedding, page_number, metadata

  `ai_conversations`                  id, user_id, context/course scope,
                                      created_at

  `ai_messages`                       id, conversation_id, role, content
                                      or protected content reference,
                                      created_at

  `ai_feedback`                       id, message_id, rating, category

  `audit_events`                      id, actor_id, action, target_type,
                                      target_id, timestamp, request_id,
                                      safe metadata

  `notification_jobs`                 id, user_id, type, scheduled_at,
                                      status, retry_count
  -----------------------------------------------------------------------

**Data-model cautions** - Do not expose quiz answer keys to the learner
before submission. - Store quiz attempt and completion history rather
than overwriting all prior results. - Add unique constraints such as one
active enrollment per user/course where appropriate. - Use indexes for
common filters: enrollment by user/status/due date; course by status;
lesson ordering; chunk retrieval filters. - Use transactions for quiz
submission and course completion updates. - Define document
deletion/version-retention behavior before launch. - Keep secrets and
access tokens out of these tables and out of audit metadata.

### 8.4 API conventions

Use `/api/v1` prefix, JSON, explicit schemas, consistent errors,
pagination, and OpenAPI documentation.

Example endpoints (not a final contract):

  -------------------------------------------------------------------------------------------
  Method                  Endpoint                                    Purpose
  ----------------------- ------------------------------------------- -----------------------
  GET                     `/api/v1/courses`                           List courses visible to
                                                                      caller

  POST                    `/api/v1/courses`                           Create course;
                                                                      author/admin only

  GET                     `/api/v1/courses/{course_id}`               Get authorized course
                                                                      details

  POST                    `/api/v1/courses/{course_id}/publish`       Publish after
                                                                      validation

  POST                    `/api/v1/courses/{course_id}/assignments`   Assign course to
                                                                      users/groups

  GET                     `/api/v1/me/learning`                       Current user's
                                                                      assignments and
                                                                      progress

  PUT                     `/api/v1/lessons/{lesson_id}/progress`      Update lesson progress

  POST                    `/api/v1/quizzes/{quiz_id}/attempts`        Start quiz attempt

  POST                    `/api/v1/attempts/{attempt_id}/submit`      Submit answers and
                                                                      score server-side

  POST                    `/api/v1/documents`                         Create upload record /
                                                                      initiate upload

  POST                    `/api/v1/documents/{document_id}/index`     Enqueue authorized
                                                                      indexing job

  GET                     `/api/v1/documents/{document_id}/status`    Check ingestion status

  POST                    `/api/v1/ai/ask`                            Ask a question about
                                                                      authorized material

  POST                    `/api/v1/ai/quiz-drafts`                    Generate quiz draft for
                                                                      authorized source
                                                                      material

  POST                    `/api/v1/ai/summary-drafts`                 Generate a summary
                                                                      draft

  GET                     `/api/v1/reports/completion`                Authorized completion
                                                                      report

  GET                     `/api/v1/admin/audit-events`                Restricted audit search
  -------------------------------------------------------------------------------------------

For long-running work, return a job identifier and status rather than
keeping the HTTP request open.

### 8.5 Example AI request/response contract

Request:

``` json
{
  "question": "What is the required process for reporting an incident?",
  "course_id": "UUID",
  "conversation_id": null
}
```

Response:

``` json
{
  "answer": "Follow the reporting steps described in the assigned incident-response course.",
  "citations": [
    {
      "document_id": "UUID",
      "document_version": 3,
      "title": "Incident Response Training",
      "page": 7,
      "chunk_id": "UUID",
      "snippet": "Relevant excerpt from the source material"
    }
  ],
  "insufficient_evidence": false,
  "request_id": "UUID"
}
```

These values are illustrative. The backend must create actual IDs and
citations from retrieved records. Do not trust client-supplied role,
permissions, document IDs, or citation details.

### 8.6 Background job lifecycle

Document ingestion states:

`uploaded → validating → queued → processing → indexed`

Failure path:

`validating/processing → failed`

Store a safe error code and retryable status. Use idempotency keys or
unique job constraints to avoid duplicate chunks when a job retries. A
re-index must be tied to a specific document version and should not
silently mix old and new chunks.

### 8.7 Course completion logic

Define completion rules explicitly. Example: - All required lessons
completed. - Required quiz passed. - Required acknowledgement submitted,
if applicable. - Completion rule version recorded with the result.

The server computes completion. Do not trust a client-provided
`completed=true` or score. Make submissions idempotent and retain
history for compliance evidence.

------------------------------------------------------------------------

## 9. Frontend design

### 9.1 Main screens

**Learner** - Home / assigned learning - Course catalog - Course detail
and modules - Lesson viewer with progress - Quiz attempt and results -
AI tutor panel with citations - My progress / certificates

**Trainer / Author** - Course editor - Module and lesson management -
Document upload and indexing status - AI summary and quiz draft review -
Publish workflow

**Manager** - Team learning overview - Completion and overdue status -
Filters by course, group, and date - Authorized export

**Administrator** - Users, groups, roles, assignments - Course lifecycle
and policy configuration - Reports, audit access, integration settings

### 9.2 UI engineering rules

-   Use typed API clients and avoid duplicating server-side business
    logic in the browser.
-   Handle loading, empty, permission-denied, validation, and
    server-error states.
-   Use accessible labels, keyboard navigation, contrast, and responsive
    layouts.
-   Do not store long-lived authentication tokens in browser local
    storage.
-   Render AI citations as links only after the API confirms the user
    can access the target source.
-   Do not expose answer keys or hidden document text in client bundles.

------------------------------------------------------------------------

## 10. Security, privacy, and compliance checklist

Before production, review with company IT/security and legal/compliance
as applicable.

### Identity and authorization

-   [ ] Company-approved SSO/OIDC or SAML.
-   [ ] Secure cookies, HTTPS, session expiration, CSRF protection where
    applicable.
-   [ ] Server-side authorization for every read/write endpoint.
-   [ ] Tests for learner/trainer/manager/admin boundaries.
-   [ ] Tenant isolation if multi-tenant.
-   [ ] Rate limits and brute-force protections at appropriate
    boundaries.

### Files and RAG

-   [ ] Private object storage with least-privilege service identities.
-   [ ] File type/size/signature validation and malware scanning.
-   [ ] Parser timeouts, resource limits, and safe handling of malformed
    files.
-   [ ] Permission filtering before retrieved text reaches the LLM.
-   [ ] Document version and deletion propagation to vector indexes and
    caches.
-   [ ] Prompt-injection tests for hostile text embedded in documents.
-   [ ] Short-lived access links and no public buckets.
-   [ ] No secrets or sensitive content in application logs.

### AI provider

-   [ ] Vendor and data-processing terms approved.
-   [ ] Retention/training-use settings reviewed.
-   [ ] Approved deployment region and network egress.
-   [ ] Secrets stored in an approved secret manager.
-   [ ] Timeouts, retry caps, quotas, cost alerts, and fallback
    behavior.
-   [ ] Model output validation and citation verification.
-   [ ] Human review before generated content is published.

### Operations

-   [ ] Dependency and container vulnerability scanning.
-   [ ] Secret scanning in CI.
-   [ ] Database backups and tested restore procedure.
-   [ ] Audit trail for role changes, publishing, assignment changes,
    and completion overrides.
-   [ ] Incident response and access revocation procedures.
-   [ ] Data retention and deletion policies.
-   [ ] Accessibility and security testing before rollout.

------------------------------------------------------------------------

## 11. GitHub reference projects

Use these repositories to learn design patterns and product behavior.
**Do not copy code wholesale into a proprietary company product without
reviewing the license and obligations.** The main repositories listed
below include copyleft licenses; get legal approval before reusing code
or distributing a modified version.

  ------------------------------------------------------------------------------------------------------------------------------------------
  Project           Repository                                                                      What to study        Caution
  ----------------- ------------------------------------------------------------------------------- -------------------- -------------------
  Moodle            https://github.com/moodle/moodle                                                Course structure,    GPL license; review
                                                                                                    roles, quizzes,      obligations before
                                                                                                    completion, plugins  copying/modifying

  Open edX platform https://github.com/openedx/openedx-platform                                     LMS/CMS              AGPL-3.0 stated in
                                                                                                    architecture, course repository; review
                                                                                                    delivery, modular    carefully
                                                                                                    platform             

  Open edX docs     https://docs.openedx.org/en/latest/developers/concepts/platform_overview.html   Platform concepts    Use for
                                                                                                    and architecture     architectural study

  Canvas LMS        https://github.com/instructure/canvas-lms                                       Course workflows,    AGPL-3.0 stated in
                                                                                                    APIs,                repository; review
                                                                                                    assessment/product   carefully
                                                                                                    patterns             

  FastAPI           https://github.com/fastapi/fastapi                                              API framework        Review license and
                                                                                                    patterns, dependency pin dependencies
                                                                                                    injection,           
                                                                                                    validation           

  SQLAlchemy        https://github.com/sqlalchemy/sqlalchemy                                        ORM and transaction  Study official docs
                                                                                                    patterns             alongside examples

  Alembic           https://github.com/sqlalchemy/alembic                                           Database migrations  Use migrations
                                                                                                                         rather than manual
                                                                                                                         production schema
                                                                                                                         edits

  LangChain         https://github.com/langchain-ai/langchain                                       Optional             Avoid unnecessary
                                                                                                    orchestration and    framework coupling
                                                                                                    retrieval            
                                                                                                    integrations         

  LlamaIndex        https://github.com/run-llama/llama_index                                        Document ingestion   Evaluate against a
                                                                                                    and retrieval        small custom
                                                                                                    patterns             pipeline before
                                                                                                                         adopting

  pgvector          https://github.com/pgvector/pgvector                                            Vector search in     Measure retrieval
                                                                                                    PostgreSQL           quality and query
                                                                                                                         performance

  Ragas             https://github.com/explodinggradients/ragas                                     RAG evaluation       Validate automated
                                                                                                    concepts             metrics against
                                                                                                                         human-reviewed
                                                                                                                         examples

  OWASP Top 10 for  https://genai.owasp.org/                                                        Threat modeling and  Convert relevant
  LLM Applications                                                                                  AI application       threats into tests
                                                                                                    security             and controls
  ------------------------------------------------------------------------------------------------------------------------------------------

### Suggested reference-study order

1.  Review Moodle and Open edX product workflows to build the feature
    checklist.
2.  Review Open edX architecture documentation, not its full codebase,
    for high-level design ideas.
3.  Use FastAPI, SQLAlchemy, Alembic, and pgvector official
    repositories/docs for implementation patterns.
4.  Build a minimal RAG proof of concept and evaluate it before adopting
    a large orchestration framework.
5.  Ask legal/security to approve any code reuse and all external AI
    services.

------------------------------------------------------------------------

## 12. Testing and acceptance criteria

### Core LMS acceptance tests

-   A learner sees only courses assigned or otherwise authorized for
    them.
-   A trainer can draft and publish only within their granted scope.
-   Quiz scores are calculated server-side.
-   Completion follows configured rules and retains history.
-   Managers see only authorized team reports.
-   Unauthorized API requests return a safe 401/403 response without
    leaking data.

### RAG acceptance tests

Create a versioned test set containing: - Answerable questions with
known source passages. - Questions whose answers are absent. - Questions
with similar wording across multiple documents. - Old and new document
versions. - Documents with different access permissions. -
Prompt-injection content inside documents. - Multilingual questions if
required.

Measure: - Retrieval recall / whether the correct evidence is found. -
Answer correctness and completeness. - Citation precision and whether
cited text supports the answer. - Appropriate abstention when evidence
is missing. - Cross-user and cross-course leakage (target: zero). -
Latency, token usage, and cost.

Do not launch AI Q&A based only on a few successful manual demos.

### Operational acceptance tests

-   Indexing jobs retry safely and do not duplicate chunks.
-   Backups can be restored.
-   Logs do not contain API keys or unnecessary personal/document
    content.
-   Rate limits and timeouts behave correctly.
-   The app remains usable when the AI provider is slow or unavailable.
-   Course content and ordinary LMS workflows still work without AI.

------------------------------------------------------------------------

## 13. Implementation roadmap

### Phase 0 --- discovery and decisions

-   Confirm users, workflows, hosting, SSO, data classification, and
    compliance requirements.
-   Define MVP acceptance criteria and UI wireframes.
-   Review licenses for every reused component.
-   Produce architecture decision records (ADRs) for major choices.

**Exit:** product scope and security constraints approved.

### Phase 1 --- platform foundation

-   Create monorepo and local Docker development environment.
-   Configure Next.js, FastAPI, PostgreSQL, migrations, tests, and CI.
-   Implement authentication integration and role-based authorization.
-   Implement audit events and structured logging.

**Exit:** users can sign in and permissions are covered by tests.

### Phase 2 --- core LMS

-   Course/module/lesson authoring.
-   Enrollment and assignments.
-   Learner course player and progress tracking.
-   Quizzes, attempts, server-side scoring, and completion.
-   Basic admin and manager reports.

**Exit:** an end-to-end course can be authored, assigned, completed, and
reported without AI.

### Phase 3 --- secure content ingestion and RAG

-   Private file upload and validation.
-   Background ingestion, chunking, embeddings, and indexing status.
-   Permission-aware retrieval and cited AI Q&A.
-   Unsupported-answer behavior and RAG evaluation suite.

**Exit:** quality and data-isolation tests pass.

### Phase 4 --- authoring assistance

-   Summary and quiz generation.
-   Structured output validation.
-   Review/edit/approve/publish workflow.
-   Cost limits and model telemetry.

**Exit:** generated content cannot be published without the required
approval.

### Phase 5 --- production hardening

-   SSO, backups, restore tests, monitoring, alerts, and incident
    procedures.
-   Load/security testing, accessibility review, privacy review, and
    retention controls.
-   Pilot with a small employee group and collect feedback.

**Exit:** IT/security and product owner approve rollout.

------------------------------------------------------------------------

## 14. OpenCode implementation workflow

OpenCode is the coding assistant, not the architecture decision-maker.
Give it bounded tasks, require tests, and review changes before merging.

### Suggested initial prompt

> Read `docs/AI_LMS_SPEC.md` completely. Do not implement the entire
> project in one pass. First produce a concise implementation plan, list
> unresolved assumptions, and propose ADRs for architecture decisions.
> Use Next.js + TypeScript for the frontend, FastAPI + Pydantic for the
> API, SQLAlchemy + Alembic for persistence, PostgreSQL for core data,
> and Redis-backed jobs only where needed. Build a modular monolith.
> Enforce server-side authorization. Keep AI provider calls behind
> interfaces. Do not invent credentials or use real company documents.
> Add tests with each feature. Do not copy code from copyleft LMS
> repositories without explicit legal approval. Begin with repository
> scaffolding and a local development environment, then stop for review.

### Task sequence for OpenCode

1.  **Scaffold:** create the repository layout, formatting/linting,
    environment example, Docker Compose for local development, and CI
    checks.
2.  **Database foundation:** SQLAlchemy models, Alembic migration,
    database session, health endpoint, and integration tests.
3.  **Authentication and authorization:** implement the chosen identity
    provider and permission dependencies; test forbidden access.
4.  **Core LMS:** implement courses, modules, lessons, enrollments,
    progress, quizzes, and completion one module at a time.
5.  **Frontend:** build typed API integration and learner/admin screens.
6.  **Document pipeline:** implement upload validation, private storage
    adapter, job state, parsers, chunking, and indexing.
7.  **RAG:** implement retrieval filters, AI provider interface,
    citation mapping, abstention, and evaluation tests.
8.  **Authoring AI:** add validated drafts and approval workflow.
9.  **Hardening:** rate limits, security tests, observability,
    backup/restore, and deployment documentation.

For each task, require OpenCode to provide: - Files changed and why. -
Database migration changes. - API contract changes. - Tests added and
actual test results. - Security/permission implications. - Known
limitations and next task.

Do not accept "tests pass" unless the tests were actually run and the
output is available. Inspect diffs and run the test suite locally before
merging.

------------------------------------------------------------------------

## 15. Environment configuration

Create `.env.example` with placeholders only. Never commit real keys.

``` dotenv
APP_ENV=development
APP_NAME=ai-lms
DATABASE_URL=postgresql+psycopg://lms:lms@localhost:5432/lms
REDIS_URL=redis://localhost:6379/0

# Configure only after choosing an approved identity provider.
OIDC_ISSUER_URL=
OIDC_CLIENT_ID=
OIDC_CLIENT_SECRET=

# Select an approved provider and model after security review.
AI_PROVIDER=
AI_MODEL=
EMBEDDING_MODEL=
AI_API_KEY=

# Private storage configuration; use workload identity/secret manager in production.
OBJECT_STORAGE_ENDPOINT=
OBJECT_STORAGE_BUCKET=
OBJECT_STORAGE_REGION=
```

These are examples, not production-ready credentials or complete
configuration. Validate required settings at startup, keep secrets in
the approved secret manager, and never put secrets in frontend
`NEXT_PUBLIC_*` variables.

------------------------------------------------------------------------

## 16. Architecture decision records to create

Create one short ADR per significant decision:

1.  `ADR-001-modular-monolith.md` --- why a modular monolith is the
    initial deployment shape.
2.  `ADR-002-identity-provider.md` --- approved SSO/OIDC/SAML approach.
3.  `ADR-003-ai-provider.md` --- hosted versus self-hosted model and
    data-handling approval.
4.  `ADR-004-vector-storage.md` --- pgvector versus a dedicated vector
    database.
5.  `ADR-005-object-storage.md` --- private storage and file access
    design.
6.  `ADR-006-course-content-format.md` --- native content model and any
    SCORM/xAPI requirement.
7.  `ADR-007-audit-retention.md` --- audit event scope and retention.

Each ADR should record context, decision, alternatives, consequences,
owner, date, and approval status.

------------------------------------------------------------------------

## 17. Final recommendation

Start with **Next.js + TypeScript, FastAPI, PostgreSQL,
SQLAlchemy/Alembic, Redis-backed background jobs, private object
storage, and a replaceable AI provider adapter**. Use
PostgreSQL/pgvector for the first RAG implementation if the company
approves it and evaluation supports it.

Prioritize the reliable LMS workflows and authorization model before AI
features. A polished chatbot cannot compensate for incorrect enrollment
rules, weak document permissions, unreliable completion records, or
unreviewed AI-generated compliance content.

The first deliverable should be a working vertical slice: sign in → open
an assigned course → complete a lesson → pass a quiz → record completion
→ show the result to an authorized manager. Add the AI tutor only after
that path and the permission boundaries are tested.
