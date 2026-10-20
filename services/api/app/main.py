import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.errors import (
    http_exception_handler,
    internal_error_handler,
    validation_error_handler,
)
from app.core.health import router as health_router
from app.core.logging import configure_logging, log_event
from app.core.middleware import RequestContextMiddleware
from app.modules.assessments.router import router as assessments_router
from app.modules.assignments.router import router as assignments_router
from app.modules.audit.router import router as audit_router
from app.modules.courses.router import admin_router as courses_admin_router
from app.modules.courses.router import router as courses_router
from app.modules.enrollments.router import router as enrollments_router
from app.modules.learners.router import router as learners_router
from app.modules.progress.router import router as progress_router
from app.modules.training_studio.router import router as studio_router
from app.modules.users.router import admin_router as users_admin_router
from app.modules.users.router import router as users_router
from app.security.errors import (
    AuthenticationError,
    AuthorizationError,
    authentication_error_handler,
    authorization_error_handler,
)
from app.security.providers import validate_auth_configuration


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    # Fail fast on unsupported/insecure configuration before serving traffic.
    validate_auth_configuration(settings)
    if settings.auth_provider == "development":
        # Temporary local-development access mode is active. Make it visible in logs.
        log_event(
            "development_access.enabled",
            level=logging.WARNING,
            outcome="warning",
            app_env=settings.app_env,
            roles=settings.dev_access_roles,
            detail="Requests run without sign-in. Local development only.",
        )
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

    # Error handlers: consistent error envelope with request correlation.
    app.add_exception_handler(AuthenticationError, authentication_error_handler)
    app.add_exception_handler(AuthorizationError, authorization_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, internal_error_handler)

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(users_admin_router, prefix="/api/v1")
    app.include_router(audit_router, prefix="/api/v1")
    app.include_router(courses_router, prefix="/api/v1")
    app.include_router(courses_admin_router, prefix="/api/v1")
    app.include_router(enrollments_router, prefix="/api/v1")
    app.include_router(learners_router, prefix="/api/v1")
    app.include_router(assignments_router, prefix="/api/v1")
    app.include_router(progress_router, prefix="/api/v1")
    app.include_router(assessments_router, prefix="/api/v1")
    app.include_router(studio_router, prefix="/api/v1")
    # Unprefixed aliases for container orchestrators that probe /healthz.
    app.include_router(health_router)
    return app


app = create_app()
