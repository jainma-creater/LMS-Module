"""Temporary local-development access mode (AUTH_PROVIDER=development).

Covers: the authoring workflow runs without sign-in; audit events are still written;
role administration and audit reads stay closed; stored roles are not changed; the
mode is refused unless APP_ENV=development; the default remains deny-by-default;
and no login or session endpoints exist. See docs/SECURITY.md.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.main import create_app
from app.modules.audit.models import AuditEvent
from app.modules.users import repository
from app.security.development import parse_development_roles
from app.security.providers import validate_auth_configuration

DEV_IDENTITY = "local-development-user"


@pytest.fixture()
def dev_env(monkeypatch):
    """Select the development provider in a development environment for one test."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTH_PROVIDER", "development")
    monkeypatch.delenv("DEV_ACCESS_ROLES", raising=False)
    get_settings.cache_clear()
    yield
    monkeypatch.undo()
    get_settings.cache_clear()


@pytest.fixture()
def dev_client(db_session, dev_env):
    """Real development provider (no stub), with only the database overridden."""
    application = create_app()

    def override_get_db():
        yield db_session

    application.dependency_overrides[get_db] = override_get_db
    with TestClient(application) as test_client:
        yield test_client
    application.dependency_overrides.clear()


def _settings(monkeypatch, **env: str) -> Settings:
    for key in ("APP_ENV", "AUTH_PROVIDER", "DEV_ACCESS_ROLES"):
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return Settings(_env_file=None)


# --------------------------------------------------------------------------- #
# Development workflow without sign-in
# --------------------------------------------------------------------------- #
def test_me_resolves_to_development_principal(dev_client):
    response = dev_client.get("/api/v1/me")
    assert response.status_code == 200
    body = response.json()
    assert body["external_identity_id"] == DEV_IDENTITY
    assert body["roles"] == ["learning_admin"]
    assert "courses:write" in body["permissions"]
    assert "courses:publish" in body["permissions"]
    assert "roles:assign" not in body["permissions"]
    assert "audit:read" not in body["permissions"]


def test_stored_roles_are_not_changed_by_development_access(dev_client, db_session):
    dev_client.get("/api/v1/me")
    user = repository.get_user_by_external_id(db_session, DEV_IDENTITY)
    assert user is not None
    assert repository.list_role_names_for_user(db_session, user.id) == ["learner"]


def test_full_course_workflow_without_sign_in(dev_client):
    c = dev_client
    created = c.post(
        "/api/v1/courses",
        json={"title": "Dev Course", "difficulty_level": "beginner", "tags": ["Pilot"]},
    )
    assert created.status_code == 201, created.text
    course = created.json()
    cid = course["id"]

    edited = c.patch(
        f"/api/v1/courses/{cid}",
        json={
            "title": "Dev Course v2",
            "short_description": "Short summary",
            "description": "Long description",
            "category": "operations",
            "difficulty_level": "intermediate",
            "estimated_minutes": 30,
            "thumbnail_url": "https://example.com/cover.png",
            "tags": ["pilot", "ops"],
        },
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["title"] == "Dev Course v2"
    assert sorted(edited.json()["tags"]) == ["ops", "pilot"]

    module = c.post(f"/api/v1/courses/{cid}/modules", json={"title": "Module 1"})
    assert module.status_code == 201
    mid = module.json()["id"]

    read = c.post(f"/api/v1/modules/{mid}/lessons", json={"title": "Read", "content": "Body"})
    assert read.status_code == 201
    watch = c.post(
        f"/api/v1/modules/{mid}/lessons",
        json={"title": "Watch", "content_type": "video_url", "content": "https://v.example/1"},
    )
    assert watch.status_code == 201
    read_id, watch_id = read.json()["id"], watch.json()["id"]

    lesson_edit = c.patch(
        f"/api/v1/lessons/{read_id}",
        json={
            "title": "Read first",
            "description": "Start here",
            "content_type": "text",
            "content": "Updated body",
            "estimated_minutes": 5,
            "is_required": True,
        },
    )
    assert lesson_edit.status_code == 200, lesson_edit.text
    assert lesson_edit.json()["description"] == "Start here"

    reorder = c.put(
        f"/api/v1/modules/{mid}/lessons/order", json={"ordered_ids": [watch_id, read_id]}
    )
    assert reorder.status_code == 200
    content = c.get(f"/api/v1/courses/{cid}/content").json()
    assert [lesson["id"] for lesson in content["modules"][0]["lessons"]] == [watch_id, read_id]

    published = c.post(f"/api/v1/courses/{cid}/publish")
    assert published.status_code == 200
    assert published.json()["status"] == "published"

    public = c.get(f"/api/v1/courses/slug/{course['slug']}")
    assert public.status_code == 200
    assert public.json()["counts"] == {"modules": 1, "lessons": 2}

    deleted = c.delete(f"/api/v1/lessons/{watch_id}")
    assert deleted.status_code == 204
    assert c.get(f"/api/v1/courses/{cid}").json()["counts"]["lessons"] == 1

    archived = c.post(f"/api/v1/courses/{cid}/archive")
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    assert c.patch(f"/api/v1/courses/{cid}", json={"title": "Too late"}).status_code == 409
    assert c.post(f"/api/v1/modules/{mid}/lessons", json={"title": "Late"}).status_code == 409

    admin_list = c.get("/api/v1/admin/courses")
    assert admin_list.status_code == 200
    assert cid in [item["id"] for item in admin_list.json()]


def test_development_access_still_validates_requests(dev_client):
    course = dev_client.post("/api/v1/courses", json={"title": "Validated"}).json()
    module = dev_client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M"}).json()
    empty_title = dev_client.post("/api/v1/courses", json={"title": ""})
    assert empty_title.status_code == 422
    bad_link = dev_client.post(
        f"/api/v1/modules/{module['id']}/lessons",
        json={"title": "Bad", "content_type": "external_link", "content": "not-a-url"},
    )
    assert bad_link.status_code == 422


def test_audit_events_are_still_written_for_development_actor(dev_client, db_session):
    course = dev_client.post("/api/v1/courses", json={"title": "Audited"}).json()
    module = dev_client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M"}).json()
    dev_client.post(f"/api/v1/modules/{module['id']}/lessons", json={"title": "L"})
    dev_client.post(f"/api/v1/courses/{course['id']}/publish")
    dev_client.post(f"/api/v1/courses/{course['id']}/archive")

    actor = repository.get_user_by_external_id(db_session, DEV_IDENTITY)
    assert actor is not None
    events = {event.action: event for event in db_session.execute(select(AuditEvent)).scalars()}
    for action in ("course.created", "course.published", "course.archived", "lesson.created"):
        assert action in events, f"missing audit event {action}"
    assert events["course.created"].actor_id == actor.id
    assert events["course.published"].actor_id == actor.id


def test_development_access_cannot_reach_role_admin_or_audit(dev_client, db_session):
    dev_client.get("/api/v1/me")
    actor = repository.get_user_by_external_id(db_session, DEV_IDENTITY)
    assert dev_client.get("/api/v1/admin/audit-events").status_code == 403
    assert (
        dev_client.post(
            f"/api/v1/admin/users/{actor.id}/roles", json={"role": "system_admin"}
        ).status_code
        == 403
    )
    assert dev_client.get(f"/api/v1/admin/users/{actor.id}/roles").status_code == 403


def test_learner_endpoints_work_in_development_mode(dev_client):
    assert dev_client.get("/api/v1/courses/categories").status_code == 200
    assert dev_client.get("/api/v1/me/learning").status_code == 200


# --------------------------------------------------------------------------- #
# Startup guards (fail closed)
# --------------------------------------------------------------------------- #
def test_default_provider_is_disabled(monkeypatch):
    _settings(monkeypatch)
    assert Settings(_env_file=None).auth_provider == "disabled"


def test_disabled_provider_is_accepted_in_any_environment(monkeypatch):
    for app_env in ("production", "test", "development"):
        settings = _settings(monkeypatch, APP_ENV=app_env, AUTH_PROVIDER="disabled")
        validate_auth_configuration(settings)  # must not raise


@pytest.mark.parametrize("app_env", ["production", "test", "staging", "", "Development", "dev"])
def test_development_provider_refused_outside_development(monkeypatch, app_env):
    settings = _settings(monkeypatch, APP_ENV=app_env, AUTH_PROVIDER="development")
    with pytest.raises(RuntimeError, match="only permitted when APP_ENV=development"):
        validate_auth_configuration(settings)


def test_development_provider_accepted_only_in_development(monkeypatch):
    settings = _settings(monkeypatch, APP_ENV="development", AUTH_PROVIDER="development")
    validate_auth_configuration(settings)  # must not raise


@pytest.mark.parametrize("provider", ["google", "oidc", "Development", "enabled", ""])
def test_unknown_provider_refused(monkeypatch, provider):
    settings = _settings(monkeypatch, APP_ENV="development", AUTH_PROVIDER=provider)
    with pytest.raises(RuntimeError, match="not implemented yet"):
        validate_auth_configuration(settings)


def test_production_app_refuses_to_start_with_development_provider(monkeypatch):
    _settings(monkeypatch, APP_ENV="production", AUTH_PROVIDER="development")
    get_settings.cache_clear()
    try:
        with (
            pytest.raises(RuntimeError, match="only permitted when APP_ENV=development"),
            TestClient(create_app()),
        ):
            pass
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


@pytest.mark.parametrize(
    "roles", ["system_admin", "learning_admin,system_admin", "nope", "", " , "]
)
def test_development_roles_are_restricted(monkeypatch, roles):
    settings = _settings(
        monkeypatch, APP_ENV="development", AUTH_PROVIDER="development", DEV_ACCESS_ROLES=roles
    )
    with pytest.raises(RuntimeError):
        validate_auth_configuration(settings)


def test_development_roles_parse_to_canonical_names():
    assert parse_development_roles(" trainer , manager ") == frozenset({"trainer", "manager"})
    assert parse_development_roles("learning_admin") == frozenset({"learning_admin"})


def test_disabled_mode_denies_authoring_requests(deny_client):
    assert deny_client.post("/api/v1/courses", json={"title": "x"}).status_code == 401
    assert deny_client.get("/api/v1/me").status_code == 401


# --------------------------------------------------------------------------- #
# No login or session surface exists
# --------------------------------------------------------------------------- #
def test_no_login_or_session_endpoints_exist(client):
    paths = create_app().openapi()["paths"]
    forbidden_fragments = ("login", "signin", "sign-in", "logout", "session", "oauth", "callback")
    for path in paths:
        lowered = path.lower()
        assert not any(fragment in lowered for fragment in forbidden_fragments), path
    assert client.get("/login").status_code == 404
    assert client.get("/api/v1/login").status_code == 404
    assert client.get("/api/v1/auth/login").status_code == 404
