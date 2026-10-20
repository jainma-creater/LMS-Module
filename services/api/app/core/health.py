from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness probe")
async def healthz() -> dict:
    """Process liveness only: no dependencies checked."""
    return {"status": "ok"}


def _schema_revision(db: Session) -> str | None:
    """Best-effort current alembic revision, or None when unavailable.

    The alembic_version table is absent before the first migration (and in
    unit-test databases created with ``create_all``), which is not a failure.
    """
    try:
        return db.execute(
            text("SELECT version_num FROM alembic_version LIMIT 1")
        ).scalar_one_or_none()
    except Exception:
        db.rollback()
        return None


@router.get("/readyz", summary="Readiness probe (checks database and schema)")
async def readyz(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    checks: dict[str, str] = {"database": "ok"}
    revision = _schema_revision(db)
    if revision is not None:
        checks["schema_revision"] = revision
    return {"status": "ready", "database": "ok", "checks": checks}
