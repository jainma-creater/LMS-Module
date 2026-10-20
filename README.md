# AI LMS

An enterprise learning management system with an AI learning assistant, built as a
modular monolith. The full product specification is in
[`AI_LMS_Project_Specification.md`](AI_LMS_Project_Specification.md).

## Status

| Area | State |
| --- | --- |
| Platform foundation (scaffolding, Docker, health endpoints, migrations) | Done |
| Auth foundation (RBAC, audit events, structured logging) | Done. Identity provider not configured. Default `disabled` returns `401`. Temporary `development` mode for local use only. |
| Core LMS (courses, modules, lessons, enrollments, progress, assessments) | Done |
| Course catalog and content (search, filters, pagination, slug lookup, tags, content types) | Done |
| Course authoring forms on `/manage` (course and lesson create/edit) | Done. Open in local `development` mode; otherwise return access-unavailable. |
| AI learning assistant / RAG | Not implemented. Provider integrations are not enabled. |

There is no sign-in page and no login route. Authentication is not implemented yet
(ADR-002). Two modes exist:

- `AUTH_PROVIDER=disabled` (default): protected endpoints return `401`.
- `AUTH_PROVIDER=development`: **temporary, local development only.** Requests run
  without sign-in as a fixed local user with the `learning_admin` role. The API refuses
  to start in this mode unless `APP_ENV=development`. See
  [Local development without sign-in](#local-development-without-sign-in).

See [`docs/SECURITY.md`](docs/SECURITY.md) and
[ADR-002](docs/adr/ADR-002-identity-provider.md).

## Technology

- **Backend:** Python 3.12–3.14, FastAPI, SQLAlchemy 2, Alembic, Pydantic, psycopg 3,
  managed with `uv`. Container image uses Python 3.13.
- **Database:** PostgreSQL 16 with the pgvector image (`pgvector/pgvector:pg16`).
- **Frontend:** Next.js 16.4 (App Router, Cache Components), React 19.3, TypeScript,
  Tailwind CSS 4, ESLint 9. Container image uses Node 24.
- **Orchestration:** Docker Compose (`compose.yaml`).

## Repository structure

```
apps/web/                 Next.js frontend (server-side API client, App Router pages)
  src/app/                Routes: /, /catalog, /courses, /learning, /progress, /manage, /quizzes
  src/app/components/     Shared UI, nav, and authoring forms
  src/lib/                Typed API client, types, form state, authoring validators
services/api/             FastAPI backend
  app/core/               Settings, logging, errors, middleware
  app/db/                 SQLAlchemy base and model registry
  app/modules/            Feature modules: users, audit, courses, enrollments, progress, assessments
  app/security/           Principal, permissions, require_permission dependency
  alembic/versions/       Migrations (0001 baseline through 0004 course catalog)
  tests/                  pytest suite
docs/                     API.md, LLD.md, SECURITY.md, adr/
infra/                    Reserved for deployment assets (currently empty)
compose.yaml              Local development stack (db, api, web)
.env.example              Configuration template (placeholders only)
```

## Prerequisites

- Docker and Docker Compose, for the full stack.
- Node.js 24 and npm, for running the frontend locally.
- Python 3.12–3.14 and [uv](https://docs.astral.sh/uv/), for running the backend locally.

## Configuration

Copy the template and edit as needed. Do not commit `.env`.

```bash
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
```

Variables the application reads today:

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | `production` disables the OpenAPI docs routes. |
| `APP_NAME` | `ai-lms` | Service name in logs. |
| `LOG_LEVEL` | `INFO` | Log level. |
| `AUTH_PROVIDER` | `disabled` | `disabled` denies protected endpoints. `development` is temporary local-only access, refused unless `APP_ENV=development`. Any other value stops the API. |
| `DEV_ACCESS_ROLES` | `learning_admin` | Roles granted in `development` mode. Comma-separated. `system_admin` is not allowed. |
| `DATABASE_URL` | `postgresql+psycopg://lms:lms@localhost:5432/lms` | Used by the API and Alembic. Compose overrides it to target the `db` service. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_PORT` | `lms` / `lms` / `lms` / `5432` | Database container settings. Local development only. |
| `API_PORT`, `WEB_PORT` | `8000`, `3000` | Host ports. |
| `API_INTERNAL_URL` | `http://localhost:8000` | Server-side URL the web app uses to reach the API. Never expose it as `NEXT_PUBLIC_*`. |

Reserved, not used by any implemented feature: `REDIS_URL`, `OIDC_ISSUER_URL`,
`OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, and the `AI_*`, `EMBEDDING_MODEL`, and
`OBJECT_STORAGE_*` entries. Leave them blank until an approved provider is configured.

## Local development without sign-in

Use this only on your own development machine. It is a temporary convenience until an
approved identity provider is added. It must not be exposed to a public, shared, or
production network.

1. Create `.env` and set the development mode:

   ```bash
   cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
   ```

   In `.env`, set:

   ```dotenv
   APP_ENV=development
   AUTH_PROVIDER=development
   DEV_ACCESS_ROLES=learning_admin
   ```

2. Start the stack. Compose binds every published port to `127.0.0.1`:

   ```bash
   docker compose up --build
   ```

3. Open http://localhost:3000. The course catalog (`/courses`), course management
   (`/manage`), and learner pages open directly. There is no login page.

What this mode does:

- Every request is treated as the local user `local-development-user`. Request headers
  and bodies cannot change the identity.
- Permissions come from `DEV_ACCESS_ROLES` (default `learning_admin`), which allows course,
  module, and lesson management, publishing, and archiving. Stored role assignments are
  not changed. `system_admin` cannot be granted, so role administration and audit reads
  return `403`.
- Authorization checks, request validation, and audit logging still run. Audit events are
  attributed to the local development user.
- The API logs a `development_access.enabled` warning at startup.

Safety rules:

- The API will not start with `AUTH_PROVIDER=development` unless `APP_ENV=development`.
- Keep `AUTH_PROVIDER=disabled` in any shared, staging, or production configuration. The
  default in `.env.example` is `disabled`.
- Do not deploy an image or `.env` that sets `AUTH_PROVIDER=development`.

To return to deny-by-default, set `AUTH_PROVIDER=disabled` and restart. No code change is
needed.

## Run with Docker Compose

```bash
cp .env.example .env
docker compose up --build        # start db, api, and web
docker compose down              # stop containers; database volume is kept
docker compose down -v           # stop and delete the local database volume (destructive)
```

- Web: http://localhost:3000
- API: http://localhost:8000 (OpenAPI docs at http://localhost:8000/api/docs outside production)
- Health: `GET /api/v1/healthz` (liveness) and `GET /api/v1/readyz` (checks the database). `/healthz` is also served unprefixed for orchestrators.

The API container runs `alembic upgrade head` before starting uvicorn.

## Run locally without Docker

Start only the database, then the API and web app in separate terminals.

```bash
docker compose up -d db

cd services/api
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

```bash
cd apps/web
npm ci
npm run dev                      # http://localhost:3000
```

The default `DATABASE_URL` already targets `localhost:5432` with the `lms` credentials,
so no change is needed when only `db` runs in Docker. If you change `POSTGRES_PORT`
because 5432 is taken, update `DATABASE_URL` to the same port.

## Database migrations

Run from `services/api`:

```bash
uv run alembic upgrade head         # apply all migrations
uv run alembic downgrade -1         # revert the most recent migration
uv run alembic check                # verify models match migrations (reports drift)
```

Applied migrations are never edited; schema changes go in a new revision. Current
head: `0008_reconcile_schema_drift`.

`alembic check` (or `alembic revision --autogenerate`) reports no drift: the model
metadata, including the `0007_query_indexes` composite indexes, matches the
database.

## Tests, lint, and build

Backend (from `services/api`):

```bash
uv run pytest
uv run ruff check .
```

Frontend (from `apps/web`):

```bash
npm test                 # validator unit tests (Node built-in test runner)
npm run lint
npm run build            # production build with type checking
npm start                # serve the production build (after npm run build)
```

## Catalog API

All routes are under `/api/v1`. Full request and response contracts are in
[`docs/API.md`](docs/API.md).

Public catalog (requires `courses:read`; drafts and archived courses are hidden):

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/courses` | Paginated page `{items, total, limit, offset}`. Filters: `search` (title, short description, description), `category`, `difficulty_level`, `tag`. `limit` 1–100 (default 20), `offset` ≥ 0. |
| GET | `/courses/categories` | Distinct categories of published courses. |
| GET | `/courses/slug/{slug}` | Published course by slug. |
| GET | `/courses/{id}` | Course detail with module and lesson counts. |
| GET | `/courses/{id}/content` | Module and lesson tree. |

Authoring (requires `courses:write`; publish and archive require `courses:publish`):

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/admin/courses` | All courses, including drafts. |
| POST | `/courses` | Create a draft. The slug is generated from the title. |
| PATCH | `/courses/{id}` | Update fields. An explicit `null` clears an optional field. `tags`, when present, replaces the set. Archived courses return `409`. |
| POST | `/courses/{id}/publish` | Requires at least one module and one lesson. |
| POST | `/courses/{id}/archive` | Archived courses are read-only. |
| POST | `/courses/{id}/modules`, `PATCH /modules/{id}`, `DELETE /modules/{id}` | Module management. |
| POST | `/modules/{id}/lessons`, `PATCH /lessons/{id}`, `DELETE /lessons/{id}` | Lesson management. |
| PUT | `/courses/{id}/modules/order`, `PUT /modules/{id}/lessons/order` | Reorder; the ID set must match exactly (`400` otherwise). |

Lesson content types are `text` (optional body), `video_url`, and `external_link`
(both require an absolute `http://` or `https://` URL). Course thumbnails must also be
http(s) URLs. Tags are stored normalized in `course_tags`: lower-cased, trimmed, and
de-duplicated, with at most 20 tags of 50 characters each.

Learning and assessment endpoints (enrollments, progress, quizzes) are documented in
[`docs/API.md`](docs/API.md).

## Authoring in the web app

- `/courses` and `/courses/[slug]` are the public catalog: search, category,
  difficulty, and tag filters with pagination; course detail with curriculum.
- `/manage` lists courses and creates them. `/manage/[courseId]` edits a course (all
  catalog fields except the slug, which the API generates), manages modules and
  lessons, assigns learners, and creates quizzes. Lesson forms cover title,
  description, content type, content, duration, and the required flag.
- The authoring pages first check `GET /admin/courses`. Without `courses:write`, they
  show an access-unavailable notice and render no forms.
- Forms validate field lengths, durations, tag limits, and URLs before submitting, and
  show field-level errors. Failed saves keep the user's input.

Limitations of the current authoring UI: the slug is read-only; a lesson cannot move
to another module (the API does not support it); module reordering exists in the API
but has no UI yet; and API validation errors that the frontend did not catch show a
general message rather than per-field detail.

## Security

- Deny by default: every protected endpoint requires an authenticated principal with the
  right permission. Failures return `401` or `403`; draft courses return `404` to callers
  without authoring rights.
- Secrets are never committed. Do not place secrets in `NEXT_PUBLIC_*` variables.
- Quiz answer keys are returned only to callers with `assessments:write`.
- See [`docs/SECURITY.md`](docs/SECURITY.md) for authentication, RBAC, auditing, and
  logging, and [`docs/adr`](docs/adr) for architecture decisions.

## Documentation

- [`AI_LMS_Project_Specification.md`](AI_LMS_Project_Specification.md): product
  specification and data model.
- [`docs/API.md`](docs/API.md): endpoint reference and permissions.
- [`docs/LLD.md`](docs/LLD.md): low-level design for courses, content, and the lifecycle.
- [`docs/SECURITY.md`](docs/SECURITY.md): security model.
- [`docs/adr`](docs/adr): architecture decision records.

## Known limitations

- Authentication is not implemented. Without `AUTH_PROVIDER=development`, authoring and
  learner data cannot be used through the web app. The development mode is not an
  identity provider, and it does not verify credentials.
- No browser-based end-to-end tests exist yet.
- AI learning assistant, RAG, embeddings, and object storage are not implemented.
- `infra/` is empty; there are no deployment manifests yet.
