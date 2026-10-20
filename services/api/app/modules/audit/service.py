"""Audit event recording.

Security-critical operations write audit rows in the same transaction as the
action so the action and its audit record commit atomically. If an audit write
fails, the exception propagates and the operation fails rather than succeeding
silently (for mutations, the caller's transaction rolls back).
"""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import context
from app.core.logging import sanitize
from app.modules.audit.models import AuditEvent, AuditOutcome

logger = logging.getLogger("ai_lms.audit")

# Audit actions. Keep names stable and namespaced by module.
ACTION_AUTH_SUCCEEDED = "auth.succeeded"
ACTION_AUTH_FAILED = "auth.failed"
ACTION_ROLE_ASSIGNED = "role.assigned"
ACTION_ROLE_REVOKED = "role.revoked"
ACTION_AUDIT_READ = "audit.read"
# Course catalog and content
ACTION_COURSE_CREATED = "course.created"
ACTION_COURSE_UPDATED = "course.updated"
ACTION_COURSE_PUBLISHED = "course.published"
ACTION_COURSE_ARCHIVED = "course.archived"
ACTION_MODULE_CREATED = "module.created"
ACTION_MODULE_UPDATED = "module.updated"
ACTION_MODULE_DELETED = "module.deleted"
ACTION_LESSON_CREATED = "lesson.created"
ACTION_LESSON_UPDATED = "lesson.updated"
ACTION_LESSON_DELETED = "lesson.deleted"
# Enrollment / assignment
ACTION_ENROLLMENT_ASSIGNED = "enrollment.assigned"
ACTION_ENROLLMENT_UPDATED = "enrollment.updated"
ACTION_ENROLLMENT_WITHDRAWN = "enrollment.withdrawn"
# Learner records, learning groups, and assignments
ACTION_LEARNER_CREATED = "learner.created"
ACTION_LEARNER_UPDATED = "learner.updated"
ACTION_GROUP_CREATED = "group.created"
ACTION_GROUP_UPDATED = "group.updated"
ACTION_GROUP_MEMBER_ADDED = "group.member_added"
ACTION_GROUP_MEMBER_REMOVED = "group.member_removed"
ACTION_ASSIGNMENT_CREATED = "assignment.created"
ACTION_ASSIGNMENT_UPDATED = "assignment.updated"
ACTION_ASSIGNMENT_CANCELLED = "assignment.cancelled"
ACTION_GROUP_ASSIGNMENT_CREATED = "group_assignment.created"
ACTION_GROUP_ASSIGNMENT_CANCELLED = "group_assignment.cancelled"
# Assessments
ACTION_QUIZ_CREATED = "quiz.created"
ACTION_QUIZ_UPDATED = "quiz.updated"
ACTION_QUIZ_PUBLISHED = "quiz.published"
ACTION_QUESTION_CREATED = "question.created"
ACTION_QUESTION_UPDATED = "question.updated"
# Learning outcomes
ACTION_COURSE_COMPLETED = "course.completed"

MAX_METADATA_KEYS = 20


def _bounded_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    if not metadata:
        return None
    sanitized = sanitize(metadata)
    if len(sanitized) > MAX_METADATA_KEYS:
        sanitized = dict(list(sanitized.items())[:MAX_METADATA_KEYS])
    return sanitized


def record_event(
    db: Session,
    *,
    action: str,
    outcome: str,
    actor_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    error_code: str | None = None,
    request_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Add an audit event to the session and flush it.

    Flushing (not committing) keeps the row in the caller's transaction. The
    caller controls commit/rollback so the action and its audit record are
    atomic.
    """
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        outcome=outcome,
        target_type=target_type,
        target_id=target_id,
        error_code=error_code,
        request_id=request_id or context.request_id_var.get(),
        event_metadata=_bounded_metadata(metadata),
    )
    db.add(event)
    db.flush()
    return event


def record_event_best_effort(db: Session, *, commit: bool = False, **kwargs: Any) -> None:
    """Record an audit event without failing the request on write errors.

    Used only where failing the request would be worse than proceeding (for
    example, recording an authentication failure). Failures are logged at
    CRITICAL so they are never silent. Set ``commit=True`` when the caller is
    about to fail the request and the row would otherwise be rolled back.
    """
    try:
        record_event(db, **kwargs)
        if commit:
            db.commit()
    except Exception:
        db.rollback()
        logger.critical(
            "audit_write_failed action=%s",
            kwargs.get("action"),
            exc_info=True,
            extra={
                "event": "audit.write_failed",
                "outcome": "failure",
                "error_code": "audit_write_failed",
            },
        )


def list_events(
    db: Session,
    *,
    limit: int = 50,
    action: str | None = None,
) -> list[AuditEvent]:
    stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    if action:
        stmt = stmt.where(AuditEvent.action == action)
    return list(db.execute(stmt).scalars())


__all__ = [
    "ACTION_AUDIT_READ",
    "ACTION_AUTH_FAILED",
    "ACTION_AUTH_SUCCEEDED",
    "ACTION_COURSE_ARCHIVED",
    "ACTION_COURSE_COMPLETED",
    "ACTION_COURSE_CREATED",
    "ACTION_COURSE_PUBLISHED",
    "ACTION_COURSE_UPDATED",
    "ACTION_ENROLLMENT_ASSIGNED",
    "ACTION_ENROLLMENT_UPDATED",
    "ACTION_LESSON_CREATED",
    "ACTION_LESSON_DELETED",
    "ACTION_LESSON_UPDATED",
    "ACTION_MODULE_CREATED",
    "ACTION_MODULE_DELETED",
    "ACTION_MODULE_UPDATED",
    "ACTION_QUESTION_CREATED",
    "ACTION_QUESTION_UPDATED",
    "ACTION_QUIZ_CREATED",
    "ACTION_QUIZ_PUBLISHED",
    "ACTION_QUIZ_UPDATED",
    "ACTION_ROLE_ASSIGNED",
    "ACTION_ROLE_REVOKED",
    "AuditOutcome",
    "list_events",
    "record_event",
    "record_event_best_effort",
]
