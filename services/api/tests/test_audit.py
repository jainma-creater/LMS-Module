"""Audit trail: security-relevant actions produce durable audit events."""

from app.modules.audit import service as audit_service


def test_role_assignment_writes_audit_event(client, make_user, login, db_session):
    admin = make_user("admin", roles=["system_admin"])
    target = make_user("target")
    login(subject="admin")

    client.post(f"/api/v1/admin/users/{target.id}/roles", json={"role": "trainer"})

    events = audit_service.list_events(db_session, action=audit_service.ACTION_ROLE_ASSIGNED)
    assert len(events) == 1
    event = events[0]
    assert event.actor_id == admin.id
    assert event.target_type == "user"
    assert event.target_id == str(target.id)
    assert event.event_metadata == {"role": "trainer"}
    assert event.outcome == "success"


def test_role_revocation_writes_audit_event(client, make_user, login, db_session):
    admin = make_user("admin", roles=["system_admin"])
    target = make_user("target", roles=["trainer"])
    login(subject="admin")

    client.delete(f"/api/v1/admin/users/{target.id}/roles/trainer")

    events = audit_service.list_events(db_session, action=audit_service.ACTION_ROLE_REVOKED)
    assert len(events) == 1
    assert events[0].actor_id == admin.id
    assert events[0].event_metadata == {"role": "trainer"}


def test_reading_audit_is_itself_audited(client, make_user, login, db_session):
    make_user("auditor", roles=["auditor"])
    login(subject="auditor")

    client.get("/api/v1/admin/audit-events")

    events = audit_service.list_events(db_session, action=audit_service.ACTION_AUDIT_READ)
    assert len(events) == 1
    assert events[0].outcome == "success"


def test_failed_authentication_is_audited(client, db_session):
    response = client.get("/api/v1/me")
    assert response.status_code == 401

    events = audit_service.list_events(db_session, action=audit_service.ACTION_AUTH_FAILED)
    assert len(events) == 1
    assert events[0].actor_id is None
    assert events[0].outcome == "failure"
    assert events[0].error_code == "missing_identity"


def test_authentication_success_recorded_on_first_login(client, login, db_session):
    login(subject="carol")
    client.get("/api/v1/me")

    events = audit_service.list_events(db_session, action=audit_service.ACTION_AUTH_SUCCEEDED)
    assert len(events) == 1
    assert events[0].event_metadata == {"provisioned": True}


def test_audit_event_carries_request_id(client, login, db_session):
    login(subject="dave")
    client.get("/api/v1/me", headers={"X-Request-ID": "trace-99"})

    events = audit_service.list_events(db_session, action=audit_service.ACTION_AUTH_SUCCEEDED)
    assert events[0].request_id == "trace-99"
