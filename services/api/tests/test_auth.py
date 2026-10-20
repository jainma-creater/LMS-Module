"""Authentication boundary: deny-by-default, no client-supplied trust."""

import uuid

from app.modules.users import repository
from app.security.principal import AuthenticatedIdentity


def test_me_requires_authentication(client):
    response = client.get("/api/v1/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthenticated"
    assert response.headers.get("www-authenticate") == "Bearer"


def test_disabled_provider_denies_all(deny_client):
    # The real (default) provider authenticates nobody.
    assert deny_client.get("/api/v1/me").status_code == 401


def test_me_returns_principal_when_authenticated(client, login):
    login(subject="alice", email="alice@example.com", name="Alice")
    response = client.get("/api/v1/me")
    assert response.status_code == 200
    body = response.json()
    assert body["external_identity_id"] == "alice"
    assert body["email"] == "alice@example.com"
    assert body["roles"] == ["learner"]
    assert "profile:read" in body["permissions"]


def test_missing_identity_rejected(client, auth_holder):
    auth_holder["identity"] = AuthenticatedIdentity(external_identity_id="   ")
    assert client.get("/api/v1/me").status_code == 401


def test_invalid_credentials_rejected(client, auth_holder):
    # Signature/expiry validation is a provider responsibility; a provider that
    # rejects credentials must yield 401 and never a principal.
    auth_holder["raise_invalid"] = True
    response = client.get("/api/v1/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


def test_client_supplied_identity_headers_are_ignored(client, login):
    login(subject="real-user")
    response = client.get(
        "/api/v1/me",
        headers={
            "X-User-Id": str(uuid.uuid4()),
            "X-Role": "system_admin",
            "X-External-Identity-Id": "attacker",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["external_identity_id"] == "real-user"
    assert body["roles"] == ["learner"]


def test_error_response_carries_request_id(client):
    response = client.get("/api/v1/me", headers={"X-Request-ID": "corr-42"})
    assert response.status_code == 401
    assert response.json()["error"]["request_id"] == "corr-42"


def test_provisioning_is_least_privilege_and_idempotent(client, login, db_session):
    login(subject="bob")
    first = client.get("/api/v1/me").json()
    second = client.get("/api/v1/me").json()
    assert first["user_id"] == second["user_id"]

    user = repository.get_user_by_external_id(db_session, "bob")
    assert repository.list_role_names_for_user(db_session, user.id) == ["learner"]
