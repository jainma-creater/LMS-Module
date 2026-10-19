# AI LMS

Enterprise Learning Management System with an AI learning assistant, built as a
**modular monolith**. See `AI_LMS_Project_Specification.md` for the full
specification.

- `apps/web` — Next.js + TypeScript frontend
- `services/api` — FastAPI + SQLAlchemy + Alembic backend
- `infra` — Docker and deployment assets
- `docs/adr` — architecture decision records

## Prerequisites

- Docker + Docker Compose
- Node.js 24 LTS and npm
- Python 3.12–3.14 and [uv](https://docs.astral.sh/uv/)

## Quick start (Docker)

```bash
cp .env.example .env        # placeholders only; edit as needed
docker compose up --build
```

- Web: http://localhost:3000
- API: http://localhost:8000 (docs at http://localhost:8000/api/docs)
- Postgres: localhost:5432

The API container runs `alembic upgrade head` before starting.

## Backend (local, without Docker)

```bash
# Start just the database
docker compose up -d db

cd services/api
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
uv run pytest
uv run ruff check .
```

## Frontend (local, without Docker)

```bash
cd apps/web
npm ci
npm run dev
npm run lint
npm run build
```

The web server reads `API_INTERNAL_URL` (server-side only) to reach the API.

## Configuration

All configuration is via environment variables. See `.env.example`. Never
commit real secrets; use an approved secret manager in production. Do not place
secrets in `NEXT_PUBLIC_*` variables.

## Roadmap

Phase 1 (current): platform foundation — repository scaffolding, local Docker
environment, configuration, health endpoints, migrations, and tests. Identity,
audit events, and the core LMS follow in subsequent milestones. AI integrations
remain behind provider interfaces and are not enabled until a provider is
approved by company security/legal.
