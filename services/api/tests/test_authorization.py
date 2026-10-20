"""Server-side RBAC: deny by default, no privilege escalation."""

import uuid


def test_learner_forbidden_role_assignment(client, make_user, login):
    target = make_user("target-1")
    login(subject="learner-user")
    response = client.post(f"/api/v1/admin/users/{target.id}/roles", json={"role": "system_admin"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_learner_forbidden_audit_read(client, login):
    login(subject="learner-audit")
    assert client.get("/api/v1/admin/audit-events").status_code == 403


def test_trainer_cannot_escalate_own_role(client, make_user, login):
    make_user("trainer-1", roles=["trainer"])
    login(subject="trainer-1")
    me = client.get("/api/v1/me").json()
    response = client.post(
        f"/api/v1/admin/users/{me['user_id']}/roles", json={"role": "system_admin"}
    )
    assert response.status_code == 403


def test_user_without_roles_has_no_permissions(client, make_user, login):
    make_user("norole-1", roles=[])
    login(subject="norole-1")
    me = client.get("/api/v1/me")
    assert me.status_code == 200
    assert me.json()["roles"] == []
    assert me.json()["permissions"] == []
    assert client.get("/api/v1/admin/audit-events").status_code == 403


def test_system_admin_can_assign_and_revoke(client, make_user, login):
    make_user("admin-1", roles=["system_admin"])
    target = make_user("target-2")
    login(subject="admin-1")

    assert (
        client.post(f"/api/v1/admin/users/{target.id}/roles", json={"role": "trainer"}).status_code
        == 204
    )
    roles = client.get(f"/api/v1/admin/users/{target.id}/roles").json()["roles"]
    assert "trainer" in roles

    # Re-assigning an existing role is a conflict, not a silent no-op.
    assert (
        client.post(f"/api/v1/admin/users/{target.id}/roles", json={"role": "trainer"}).status_code
        == 409
    )

    assert client.delete(f"/api/v1/admin/users/{target.id}/roles/trainer").status_code == 204
    roles = client.get(f"/api/v1/admin/users/{target.id}/roles").json()["roles"]
    assert "trainer" not in roles


def test_auditor_can_read_audit_but_not_assign(client, make_user, login):
    make_user("auditor-1", roles=["auditor"])
    target = make_user("target-3")
    login(subject="auditor-1")

    assert client.get("/api/v1/admin/audit-events").status_code == 200
    assert (
        client.post(f"/api/v1/admin/users/{target.id}/roles", json={"role": "trainer"}).status_code
        == 403
    )


def test_assign_unknown_role_returns_404(client, make_user, login):
    make_user("admin-2", roles=["system_admin"])
    target = make_user("target-4")
    login(subject="admin-2")
    response = client.post(f"/api/v1/admin/users/{target.id}/roles", json={"role": "not_a_role"})
    assert response.status_code == 404


def test_assign_role_to_unknown_user_returns_404(client, make_user, login):
    make_user("admin-3", roles=["system_admin"])
    login(subject="admin-3")
    response = client.post(f"/api/v1/admin/users/{uuid.uuid4()}/roles", json={"role": "trainer"})
    assert response.status_code == 404


def test_revoke_unassigned_role_returns_409(client, make_user, login):
    make_user("admin-4", roles=["system_admin"])
    target = make_user("target-5")
    login(subject="admin-4")
    response = client.delete(f"/api/v1/admin/users/{target.id}/roles/trainer")
    assert response.status_code == 409
