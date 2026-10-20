"""Structured JSON logging with request/actor correlation and secret redaction.

All application logs are emitted as single-line JSON objects. Use
``log_event()`` for structured events so fields are redacted consistently.
Never log raw request bodies, credentials, tokens, or document contents.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core import context
from app.core.config import get_settings

REDACTED = "[REDACTED]"

# A key is redacted when its lowercased name contains any of these fragments.
SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "api_key",
    "apikey",
    "client_secret",
    "signing_key",
    "private_key",
    "credential",
)


def is_sensitive_key(key: Any) -> bool:
    lowered = str(key).lower()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def sanitize(value: Any) -> Any:
    """Recursively redact sensitive mapping keys in nested structures."""
    if isinstance(value, dict):
        return {
            key: (REDACTED if is_sensitive_key(key) else sanitize(item))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    """Render log records as a single JSON line with correlation fields."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", None) or record.getMessage(),
            "request_id": getattr(record, "request_id", None) or context.request_id_var.get(),
            "actor_id": getattr(record, "actor_id", None) or context.actor_id_var.get(),
        }

        for attr in ("outcome", "error_code"):
            value = getattr(record, attr, None)
            if value is not None:
                payload[attr] = value

        fields = getattr(record, "fields", None)
        if fields:
            payload["details"] = sanitize(fields)

        if getattr(record, "event", None):
            payload["message"] = record.getMessage()

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


_event_logger = logging.getLogger("ai_lms.event")


def log_event(
    event: str,
    *,
    level: int = logging.INFO,
    outcome: str | None = None,
    error_code: str | None = None,
    request_id: str | None = None,
    actor_id: str | None = None,
    **fields: Any,
) -> None:
    """Emit a structured, redacted event log record."""
    _event_logger.log(
        level,
        event,
        extra={
            "event": event,
            "outcome": outcome,
            "error_code": error_code,
            "request_id": request_id,
            "actor_id": actor_id,
            "fields": fields,
        },
    )


def configure_logging() -> None:
    settings = get_settings()
    # Tests emit their own handlers; avoid clobbering the test logging setup.
    if settings.is_testing:
        return

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)

    # Never let third-party loggers leak secrets at DEBUG in production.
    if settings.is_production and level < logging.INFO:
        for noisy in ("uvicorn.access", "httpx", "httpcore"):
            logging.getLogger(noisy).setLevel(logging.INFO)
