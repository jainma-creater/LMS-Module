# AI LMS API

FastAPI backend for the AI LMS modular monolith.

## Development

```bash
uv sync          # install deps (creates .venv, uv.lock already committed)
uv run pytest    # run tests
uv run ruff check .
uv run uvicorn app.main:app --reload --port 8000
```

Configuration is read from environment / `.env` (see repo-root `.env.example`).
Database schema changes go through Alembic (`alembic upgrade head`).
