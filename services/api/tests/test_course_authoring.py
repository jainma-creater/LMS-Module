"""Authoring contract used by the /manage forms (course and lesson create/edit).

Covers: full field round-trips, explicit-null clearing, tag replacement in the
normalized course_tags table, server-side validation (durations, URLs, content
types, tag limits), and authorization (deny-by-default, learner denial, archived
read-only).
"""

import uuid

import pytest
from sqlalchemy import select

from app.modules.courses.models import CourseTag

MISSING_ID = "00000000-0000-4000-8000-000000000000"

FULL_COURSE = {
    "title": "Fire Safety",
    "short_description": "Know the exits.",
    "description": "Full description text.",
    "category": "compliance",
    "difficulty_level": "advanced",
    "estimated_minutes": 45,
    "thumbnail_url": "https://example.com/cover.png",
    "tags": ["safety", "onboarding"],
}


def _create_course(client, **overrides) -> dict:
    response = client.post("/api/v1/courses", json={**FULL_COURSE, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def _add_module(client, course_id) -> dict:
    response = client.post(f"/api/v1/courses/{course_id}/modules", json={"title": "M1"})
    assert response.status_code == 201, response.text
    return response.json()


def _add_lesson(client, module_id, **fields) -> dict:
    response = client.post(f"/api/v1/modules/{module_id}/lessons", json={"title": "L1", **fields})
    assert response.status_code == 201, response.text
    return response.json()


def _tag_rows(db_session, course_id) -> list[str]:
    stmt = (
        select(CourseTag.tag)
        .where(CourseTag.course_id == uuid.UUID(course_id))
        .order_by(CourseTag.tag)
    )
    return list(db_session.execute(stmt).scalars().all())


@pytest.fixture()
def trainer(make_user, login):
    make_user("author-trainer", roles=["trainer"])
    login(subject="author-trainer")
    return "author-trainer"


# --------------------------------------------------------------------------- #
# Course edit behavior
# --------------------------------------------------------------------------- #
def test_patch_course_updates_every_authoring_field(client, trainer, db_session):
    course = _create_course(client)
    changes = {
        "title": "Fire Safety 2",
        "short_description": "Updated summary.",
        "description": "Updated body.",
        "category": "operations",
        "difficulty_level": "intermediate",
        "estimated_minutes": 90,
        "thumbnail_url": "https://cdn.example.com/new.jpg",
        "tags": ["Ops", "fire"],
    }
    response = client.patch(f"/api/v1/courses/{course['id']}", json=changes)
    assert response.status_code == 200, response.text
    body = response.json()
    for field in ("title", "short_description", "description", "category", "difficulty_level"):
        assert body[field] == changes[field]
    assert body["estimated_minutes"] == 90
    assert body["thumbnail_url"] == "https://cdn.example.com/new.jpg"
    assert sorted(body["tags"]) == ["fire", "ops"]
    assert _tag_rows(db_session, course["id"]) == ["fire", "ops"]

    detail = client.get(f"/api/v1/courses/{course['id']}").json()
    assert detail["title"] == "Fire Safety 2"
    assert sorted(detail["tags"]) == ["fire", "ops"]


def test_patch_with_explicit_nulls_clears_optional_fields(client, trainer, db_session):
    course = _create_course(client)
    response = client.patch(
        f"/api/v1/courses/{course['id']}",
        json={
            "title": "Fire Safety",
            "short_description": None,
            "description": None,
            "category": None,
            "difficulty_level": "beginner",
            "estimated_minutes": None,
            "thumbnail_url": None,
            "tags": [],
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["short_description"] is None
    assert body["description"] is None
    assert body["category"] is None
    assert body["estimated_minutes"] is None
    assert body["thumbnail_url"] is None
    assert body["tags"] == []
    assert _tag_rows(db_session, course["id"]) == []


def test_patch_without_tags_key_keeps_existing_tags(client, trainer, db_session):
    course = _create_course(client)
    response = client.patch(f"/api/v1/courses/{course['id']}", json={"title": "Renamed"})
    assert response.status_code == 200
    assert sorted(response.json()["tags"]) == ["onboarding", "safety"]
    assert _tag_rows(db_session, course["id"]) == ["onboarding", "safety"]


def test_patch_replaces_tags_without_duplicate_rows(client, trainer, db_session):
    course = _create_course(client, tags=["a", "b"])
    response = client.patch(f"/api/v1/courses/{course['id']}", json={"tags": ["C", "c", " c "]})
    assert response.status_code == 200, response.text
    assert response.json()["tags"] == ["c"]
    assert _tag_rows(db_session, course["id"]) == ["c"]


def test_slug_is_not_changed_by_title_edit(client, trainer):
    course = _create_course(client, title="Original Title")
    response = client.patch(f"/api/v1/courses/{course['id']}", json={"title": "Другой заголовок"})
    assert response.status_code == 200
    assert response.json()["slug"] == course["slug"]


@pytest.mark.parametrize(
    "payload",
    [
        {"title": ""},
        {"estimated_minutes": -1},
        {"estimated_minutes": 60001},
        {"thumbnail_url": "javascript:alert(1)"},
        {"thumbnail_url": "ftp://example.com/x.png"},
        {"difficulty_level": "expert"},
    ],
)
def test_patch_rejects_invalid_values_and_leaves_course_unchanged(client, trainer, payload):
    course = _create_course(client)
    response = client.patch(f"/api/v1/courses/{course['id']}", json=payload)
    assert response.status_code == 422, response.text
    detail = client.get(f"/api/v1/courses/{course['id']}").json()
    assert detail["title"] == FULL_COURSE["title"]
    assert detail["estimated_minutes"] == FULL_COURSE["estimated_minutes"]


def test_create_rejects_too_many_tags_and_overlong_tag(client, trainer):
    too_many = [f"tag{i}" for i in range(21)]
    response = client.post("/api/v1/courses", json={"title": "X", "tags": too_many})
    assert response.status_code == 422

    response = client.post("/api/v1/courses", json={"title": "X", "tags": ["t" * 51]})
    assert response.status_code == 422


def test_patch_unknown_course_returns_404(client, trainer):
    response = client.patch(f"/api/v1/courses/{MISSING_ID}", json={"title": "Nope"})
    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# Lesson create/edit behavior
# --------------------------------------------------------------------------- #
def test_lesson_patch_changes_type_and_round_trips_description(client, trainer):
    course = _create_course(client)
    module = _add_module(client, course["id"])
    lesson = _add_lesson(
        client, module["id"], description="Overview", content="Read this.", estimated_minutes=5
    )

    response = client.patch(
        f"/api/v1/lessons/{lesson['id']}",
        json={
            "title": "Watch",
            "description": "Overview",
            "content_type": "video_url",
            "content": "https://video.example.com/v/1",
            "estimated_minutes": 12,
            "is_required": False,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["content_type"] == "video_url"
    assert body["content"] == "https://video.example.com/v/1"
    assert body["description"] == "Overview"
    assert body["estimated_minutes"] == 12
    assert body["is_required"] is False


def test_lesson_patch_null_description_clears_it(client, trainer):
    course = _create_course(client)
    module = _add_module(client, course["id"])
    lesson = _add_lesson(client, module["id"], description="Remove me")
    response = client.patch(f"/api/v1/lessons/{lesson['id']}", json={"description": None})
    assert response.status_code == 200
    assert response.json()["description"] is None


def test_lesson_text_type_may_clear_content(client, trainer):
    course = _create_course(client)
    module = _add_module(client, course["id"])
    lesson = _add_lesson(client, module["id"], content="Some text")
    response = client.patch(f"/api/v1/lessons/{lesson['id']}", json={"content": None})
    assert response.status_code == 200
    assert response.json()["content"] is None


def test_lesson_link_type_cannot_clear_content(client, trainer):
    course = _create_course(client)
    module = _add_module(client, course["id"])
    lesson = _add_lesson(
        client,
        module["id"],
        content_type="external_link",
        content="https://example.com/doc",
    )
    response = client.patch(f"/api/v1/lessons/{lesson['id']}", json={"content": None})
    assert response.status_code == 422


@pytest.mark.parametrize("legacy", ["video", "link", "file"])
def test_legacy_lesson_content_types_are_rejected(client, trainer, legacy):
    course = _create_course(client)
    module = _add_module(client, course["id"])
    created = client.post(
        f"/api/v1/modules/{module['id']}/lessons",
        json={"title": "Old", "content_type": legacy, "content": "https://example.com"},
    )
    assert created.status_code == 422

    lesson = _add_lesson(client, module["id"])
    patched = client.patch(f"/api/v1/lessons/{lesson['id']}", json={"content_type": legacy})
    assert patched.status_code == 422


def test_lesson_negative_duration_is_rejected(client, trainer):
    course = _create_course(client)
    module = _add_module(client, course["id"])
    response = client.post(
        f"/api/v1/modules/{module['id']}/lessons",
        json={"title": "Bad", "estimated_minutes": -3},
    )
    assert response.status_code == 422


def test_lesson_patch_unknown_returns_404(client, trainer):
    response = client.patch(f"/api/v1/lessons/{MISSING_ID}", json={"title": "Nope"})
    assert response.status_code == 404


# --------------------------------------------------------------------------- #
# Authorization and lifecycle
# --------------------------------------------------------------------------- #
def test_patch_course_and_lesson_require_authentication(deny_client):
    course_patch = deny_client.patch(f"/api/v1/courses/{MISSING_ID}", json={"title": "x"})
    lesson_patch = deny_client.patch(f"/api/v1/lessons/{MISSING_ID}", json={"title": "x"})
    assert course_patch.status_code == 401
    assert lesson_patch.status_code == 401
    assert (
        deny_client.post(f"/api/v1/modules/{MISSING_ID}/lessons", json={"title": "x"}).status_code
        == 401
    )


def test_learner_cannot_patch_course_or_lesson(client, make_user, login):
    make_user("author-for-learner", roles=["trainer"])
    login(subject="author-for-learner")
    course = _create_course(client)
    module = _add_module(client, course["id"])
    lesson = _add_lesson(client, module["id"])

    make_user("plain-learner", roles=["learner"])
    login(subject="plain-learner")
    assert client.patch(f"/api/v1/courses/{course['id']}", json={"title": "x"}).status_code == 403
    assert client.patch(f"/api/v1/lessons/{lesson['id']}", json={"title": "x"}).status_code == 403
    assert (
        client.post(f"/api/v1/modules/{module['id']}/lessons", json={"title": "x"}).status_code
        == 403
    )


def test_archived_course_rejects_course_and_lesson_edits(client, make_user, login):
    make_user("archiver", roles=["learning_admin"])
    login(subject="archiver")
    course = _create_course(client)
    module = _add_module(client, course["id"])
    lesson = _add_lesson(client, module["id"])
    assert client.post(f"/api/v1/courses/{course['id']}/archive").status_code == 200

    assert client.patch(f"/api/v1/courses/{course['id']}", json={"title": "x"}).status_code == 409
    assert client.patch(f"/api/v1/lessons/{lesson['id']}", json={"title": "x"}).status_code == 409
