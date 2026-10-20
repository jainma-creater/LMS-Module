import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core import context
from app.core.logging import log_event

REQUEST_ID_HEADER = "X-Request-ID"
PROCESS_TIME_HEADER = "X-Process-Time-Ms"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request ID and emit structured request start/finish events."""

    async def dispatch(self, request: Request, call_next):
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming if incoming else str(uuid.uuid4())
        request.state.request_id = request_id
        context.request_id_var.set(request_id)

        log_event("request.started", method=request.method, path=request.url.path)

        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)

        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[PROCESS_TIME_HEADER] = f"{duration_ms:.2f}"
        actor_id = getattr(request.state, "actor_id", None)
        outcome = "success" if response.status_code < 400 else "failure"
        log_event(
            "request.finished",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            outcome=outcome,
            actor_id=actor_id,
            duration_ms=duration_ms,
            level=logging.INFO,
        )
        return response
