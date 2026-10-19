from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.errors import internal_error_handler, not_found_handler
from app.core.health import router as health_router
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Fail fast on missing/invalid configuration is handled by Settings itself.
    # Extend with approved-provider validation here as integrations land.
    app.state.settings = settings
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if not settings.is_production else None,
        redoc_url=None,
    )
    app.add_middleware(RequestContextMiddleware)
    app.add_exception_handler(Exception, internal_error_handler)
    app.add_exception_handler(404, not_found_handler)
    app.include_router(health_router, prefix="/api/v1")
    # Unprefixed aliases for container orchestrators that probe /healthz.
    app.include_router(health_router)
    return app


app = create_app()
