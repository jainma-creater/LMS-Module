"""Structured logging: JSON output and secret redaction."""

import io
import json
import logging

from app.core.logging import JsonFormatter, configure_logging, log_event


def _capture(logger: logging.Logger, formatter: logging.Formatter):
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return stream, handler


def test_json_formatter_emits_correlation_fields():
    logger = logging.getLogger("test.json")
    stream, handler = _capture(logger, JsonFormatter())
    try:
        logger.info(
            "something happened",
            extra={"event": "request.started", "outcome": "success"},
        )
    finally:
        logger.removeHandler(handler)

    payload = json.loads(stream.getvalue().strip())
    assert payload["event"] == "request.started"
    assert payload["level"] == "INFO"
    assert "timestamp" in payload
    assert "request_id" in payload


def test_log_event_redacts_sensitive_fields():
    logger = logging.getLogger("ai_lms.event")
    stream, handler = _capture(logger, JsonFormatter())
    try:
        log_event(
            "auth.attempt",
            password="hunter2",
            access_token="secret-token-value",
            user="alice",
        )
    finally:
        logger.removeHandler(handler)

    line = stream.getvalue().strip()
    assert "hunter2" not in line
    assert "secret-token-value" not in line

    payload = json.loads(line)
    details = payload["details"]
    assert details["password"] == "[REDACTED]"
    assert details["access_token"] == "[REDACTED]"
    assert details["user"] == "alice"


def test_error_code_is_included_when_present():
    logger = logging.getLogger("ai_lms.event")
    stream, handler = _capture(logger, JsonFormatter())
    try:
        log_event("authorization.denied", outcome="failure", error_code="forbidden")
    finally:
        logger.removeHandler(handler)

    payload = json.loads(stream.getvalue().strip())
    assert payload["outcome"] == "failure"
    assert payload["error_code"] == "forbidden"


def test_configure_logging_installs_json_formatter(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("APP_ENV", "development")
    get_settings.cache_clear()

    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    try:
        configure_logging()
        assert any(isinstance(h.formatter, JsonFormatter) for h in root.handlers)
    finally:
        for handler in list(root.handlers):
            root.removeHandler(handler)
        for handler in saved_handlers:
            root.addHandler(handler)
        root.setLevel(saved_level)
        get_settings.cache_clear()
