"""Restricted audit-report endpoints.

Access requires the ``audit:read`` permission. Reading audit data is itself
audited, and the read is performed and committed before the read event is
written so the access record does not appear in the returned results.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.audit import service
from app.modules.audit.models import AuditOutcome
from app.modules.audit.schemas import AuditEventResponse
from app.security.dependencies import require_permission
from app.security.permissions import Permission
from app.security.principal import Principal

router = APIRouter(prefix="/admin", tags=["audit"])


@router.get("/audit-events", response_model=list[AuditEventResponse])
def list_audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    action: str | None = Query(default=None, max_length=100),
    principal: Principal = Depends(require_permission(Permission.AUDIT_READ)),
    db: Session = Depends(get_db),
) -> list[AuditEventResponse]:
    events = service.list_events(db, limit=limit, action=action)
    response = [AuditEventResponse.model_validate(event) for event in events]
    service.record_event(
        db,
        action=service.ACTION_AUDIT_READ,
        outcome=AuditOutcome.SUCCESS,
        actor_id=principal.user_id,
        target_type="audit_events",
        metadata={"limit": limit, "action_filter": action, "returned": len(events)},
    )
    db.commit()
    return response
