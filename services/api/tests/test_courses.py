"""Course catalog, authoring, and authorization tests.

Unauthenticated access is denied; permissions are enforced per endpoint; draft
courses never leak to callers without authoring rights.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.audit.models import AuditEvent


def _create_course(client, title="Intro to Safety") -> dict:
    response = client.post("/api/v1/courses", json={"title": title})
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------- #
# Deny-by-default
# --------------------------------------------------------------------------- #
def test_catalog_requires_authentication(deny_client):
    response = deny_client.get("/api/v1/courses")
    assert response.status_code == 401


def test_course_creation_requires_authentication(deny_client):
    response = deny_client.post("/api/v1/courses", json={"title": "Nope"})
    assert response.status_code == 401


def test_publish_requires_authentication(deny_client):
    response = deny_client.post("/api/v1/courses/00000000-0000-4000-8000-000000000000/publish")
    assert response.status_code == 401


# --------------------------------------------------------------------------- #
# Authorization
# --------------------------------------------------------------------------- #
def test_learner_cannot_create_course(client, make_user, login):
    make_user("learner-1", roles=["learner"])
    login(subject="learner-1")
    response = client.post("/api/v1/courses", json={"title": "Forbidden"})
    assert response.status_code == 403


def test_trainer_cannot_publish(client, make_user, login):
    make_user("trainer-1", roles=["trainer"])
    login(subject="trainer-1")
    course = _create_course(client)
    response = client.post(f"/api/v1/courses/{course['id']}/publish")
    assert response.status_code == 403


# --------------------------------------------------------------------------- #
# Authoring lifecycle
# --------------------------------------------------------------------------- #
def test_trainer_creates_course_with_slug(client, make_user, login, db_session):
    make_user("trainer-2", roles=["trainer"])
    login(subject="trainer-2")
    course = _create_course(client, title="Fire Safety 101")
    assert course["slug"] == "fire-safety-101"
    assert course["status"] == "draft"
    assert course["version"] == 1

    events = list(db_session.execute(select(AuditEvent)).scalars())
    assert any(event.action == "course.created" for event in events)


def test_duplicate_titles_get_unique_slugs(client, make_user, login):
    make_user("trainer-3", roles=["trainer"])
    login(subject="trainer-3")
    first = _create_course(client, title="Same Title")
    second = _create_course(client, title="Same Title")
    assert first["slug"] == "same-title"
    assert second["slug"] == "same-title-2"


def test_draft_course_is_hidden_from_learners(client, make_user, login):
    make_user("trainer-4", roles=["trainer"])
    login(subject="trainer-4")
    course = _create_course(client)

    make_user("learner-2", roles=["learner"])
    login(subject="learner-2")
    assert client.get(f"/api/v1/courses/{course['id']}").status_code == 404
    assert client.get("/api/v1/courses").json()["items"] == []


def test_published_course_is_visible_to_learners(client, make_user, login):
    make_user("admin-1", roles=["learning_admin"])
    login(subject="admin-1")
    course = _create_course(client, title="Published Course")
    module = client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M1"}).json()
    client.post(f"/api/v1/modules/{module['id']}/lessons", json={"title": "L1"})
    published = client.post(f"/api/v1/courses/{course['id']}/publish")
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["published_at"] is not None

    make_user("learner-3", roles=["learner"])
    login(subject="learner-3")
    catalog = client.get("/api/v1/courses").json()
    assert [item["id"] for item in catalog["items"]] == [course["id"]]
    assert catalog["total"] == 1
    assert client.get(f"/api/v1/courses/{course['id']}").status_code == 200


def test_publish_twice_conflicts(client, make_user, login):
    make_user("admin-2", roles=["learning_admin"])
    login(subject="admin-2")
    course = _create_course(client)
    module = client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M1"}).json()
    client.post(f"/api/v1/modules/{module['id']}/lessons", json={"title": "L1"})
    client.post(f"/api/v1/courses/{course['id']}/publish")
    response = client.post(f"/api/v1/courses/{course['id']}/publish")
    assert response.status_code == 409


def test_publish_without_content_conflicts(client, make_user, login):
    make_user("admin-empty", roles=["learning_admin"])
    login(subject="admin-empty")
    course = _create_course(client, title="Empty Course")
    response = client.post(f"/api/v1/courses/{course['id']}/publish")
    assert response.status_code == 409

    # A module alone is not enough; a lesson is required too.
    client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M1"})
    assert client.post(f"/api/v1/courses/{course['id']}/publish").status_code == 409


def test_archived_course_cannot_be_published(client, make_user, login):
    make_user("admin-arch", roles=["learning_admin"])
    login(subject="admin-arch")
    course = _create_course(client)
    module = client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M1"}).json()
    client.post(f"/api/v1/modules/{module['id']}/lessons", json={"title": "L1"})
    client.post(f"/api/v1/courses/{course['id']}/archive")
    response = client.post(f"/api/v1/courses/{course['id']}/publish")
    assert response.status_code == 409


# --------------------------------------------------------------------------- #
# Modules and lessons
# --------------------------------------------------------------------------- #
def test_module_and_lesson_ordering(client, make_user, login):
    make_user("trainer-5", roles=["trainer"])
    login(subject="trainer-5")
    course = _create_course(client)

    first = client.post(
        f"/api/v1/courses/{course['id']}/modules", json={"title": "Module A"}
    ).json()
    second = client.post(
        f"/api/v1/courses/{course['id']}/modules", json={"title": "Module B"}
    ).json()
    assert first["sort_order"] == 0
    assert second["sort_order"] == 1

    reordered = client.put(
        f"/api/v1/courses/{course['id']}/modules/order",
        json={"ordered_ids": [second["id"], first["id"]]},
    )
    assert reordered.status_code == 200
    assert [m["id"] for m in reordered.json()] == [second["id"], first["id"]]

    lesson = client.post(
        f"/api/v1/modules/{first['id']}/lessons",
        json={"title": "Lesson 1", "content": "Read this."},
    )
    assert lesson.status_code == 201
    assert lesson.json()["sort_order"] == 0


def test_invalid_reorder_rejected(client, make_user, login):
    make_user("trainer-6", roles=["trainer"])
    login(subject="trainer-6")
    course = _create_course(client)
    client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "Module A"})
    response = client.put(
        f"/api/v1/courses/{course['id']}/modules/order",
        json={"ordered_ids": ["00000000-0000-4000-8000-000000000000"]},
    )
    assert response.status_code == 400


def test_archived_course_cannot_be_edited(client, make_user, login):
    make_user("admin-3", roles=["learning_admin"])
    login(subject="admin-3")
    course = _create_course(client)
    client.post(f"/api/v1/courses/{course['id']}/archive")
    response = client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "Too late"})
    assert response.status_code == 409


def test_course_content_tree(client, make_user, login):
    make_user("trainer-7", roles=["trainer"])
    login(subject="trainer-7")
    course = _create_course(client)
    module = client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M1"}).json()
    client.post(f"/api/v1/modules/{module['id']}/lessons", json={"title": "L1"})
    client.post(f"/api/v1/modules/{module['id']}/lessons", json={"title": "L2"})

    content = client.get(f"/api/v1/courses/{course['id']}/content")
    assert content.status_code == 200
    body = content.json()
    assert body["course"]["id"] == course["id"]
    assert [lesson["title"] for lesson in body["modules"][0]["lessons"]] == ["L1", "L2"]


def _publish_with_lesson(client, title, **course_fields) -> dict:
    course = client.post("/api/v1/courses", json={"title": title, **course_fields}).json()
    module = client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M1"}).json()
    client.post(f"/api/v1/modules/{module['id']}/lessons", json={"title": "L1"})
    response = client.post(f"/api/v1/courses/{course['id']}/publish")
    assert response.status_code == 200, response.text
    detail = client.get(f"/api/v1/courses/{course['id']}")
    assert detail.status_code == 200
    return detail.json()


def test_slug_endpoint_returns_published_course(client, make_user, login):
    make_user("admin-slug", roles=["learning_admin"])
    login(subject="admin-slug")
    course = _publish_with_lesson(client, "Slug Course")

    make_user("learner-slug", roles=["learner"])
    login(subject="learner-slug")
    response = client.get(f"/api/v1/courses/slug/{course['slug']}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == course["id"]
    assert body["counts"] == {"modules": 1, "lessons": 1}


def test_slug_endpoint_hides_drafts(client, make_user, login):
    make_user("trainer-slug", roles=["trainer"])
    login(subject="trainer-slug")
    course = _create_course(client, title="Draft By Slug")
    assert client.get(f"/api/v1/courses/slug/{course['slug']}").status_code == 404


def test_categories_lists_published_only(client, make_user, login):
    make_user("admin-cat", roles=["learning_admin"])
    login(subject="admin-cat")
    _publish_with_lesson(client, "Cat A", category="compliance")
    _publish_with_lesson(client, "Cat B", category="engineering")
    _create_course(client, title="Draft Cat")

    make_user("learner-cat", roles=["learner"])
    login(subject="learner-cat")
    assert client.get("/api/v1/courses/categories").json() == ["compliance", "engineering"]


def test_search_filter_matches_title_and_description(client, make_user, login):
    make_user("admin-search", roles=["learning_admin"])
    login(subject="admin-search")
    _publish_with_lesson(client, "Fire Safety Basics")
    _publish_with_lesson(client, "Data Privacy", description="Handling personal data")

    make_user("learner-search", roles=["learner"])
    login(subject="learner-search")
    fire = client.get("/api/v1/courses", params={"search": "fire"}).json()
    assert [item["title"] for item in fire["items"]] == ["Fire Safety Basics"]
    privacy = client.get("/api/v1/courses", params={"search": "personal data"}).json()
    assert [item["title"] for item in privacy["items"]] == ["Data Privacy"]


def test_category_and_difficulty_filters(client, make_user, login):
    make_user("admin-filter", roles=["learning_admin"])
    login(subject="admin-filter")
    _publish_with_lesson(client, "Easy Comp", category="compliance", difficulty_level="beginner")
    _publish_with_lesson(client, "Hard Eng", category="engineering", difficulty_level="advanced")

    make_user("learner-filter", roles=["learner"])
    login(subject="learner-filter")
    by_cat = client.get("/api/v1/courses", params={"category": "engineering"}).json()
    assert [item["title"] for item in by_cat["items"]] == ["Hard Eng"]
    by_diff = client.get("/api/v1/courses", params={"difficulty_level": "beginner"}).json()
    assert [item["title"] for item in by_diff["items"]] == ["Easy Comp"]


def test_tag_filter_and_normalisation(client, make_user, login):
    make_user("admin-tags", roles=["learning_admin"])
    login(subject="admin-tags")
    tagged = _publish_with_lesson(
        client, "Tagged Course", tags=["Security", "security", " Onboarding "]
    )
    assert tagged["tags"] == ["onboarding", "security"]
    _publish_with_lesson(client, "Untagged Course")

    make_user("learner-tags", roles=["learner"])
    login(subject="learner-tags")
    filtered = client.get("/api/v1/courses", params={"tag": "security"}).json()
    assert [item["title"] for item in filtered["items"]] == ["Tagged Course"]


def test_pagination_envelope_and_deterministic_order(client, make_user, login):
    make_user("admin-page", roles=["learning_admin"])
    login(subject="admin-page")
    for index in range(3):
        _publish_with_lesson(client, f"Paged {index}")

    make_user("learner-page", roles=["learner"])
    login(subject="learner-page")
    first = client.get("/api/v1/courses", params={"limit": 2, "offset": 0}).json()
    assert first["total"] == 3
    assert len(first["items"]) == 2

    second = client.get("/api/v1/courses", params={"limit": 2, "offset": 2}).json()
    assert second["total"] == 3
    assert len(second["items"]) == 1
    first_ids = {item["id"] for item in first["items"]}
    second_ids = {item["id"] for item in second["items"]}
    assert first_ids.isdisjoint(second_ids)

    repeat = client.get("/api/v1/courses", params={"limit": 2, "offset": 0}).json()
    assert [item["id"] for item in repeat["items"]] == [item["id"] for item in first["items"]]


def test_invalid_pagination_rejected(client, make_user, login):
    make_user("learner-page2", roles=["learner"])
    login(subject="learner-page2")
    assert client.get("/api/v1/courses", params={"limit": 0}).status_code == 422
    assert client.get("/api/v1/courses", params={"limit": 500}).status_code == 422
    assert client.get("/api/v1/courses", params={"offset": -1}).status_code == 422


def test_archived_course_excluded_from_catalog(client, make_user, login):
    make_user("admin-arch2", roles=["learning_admin"])
    login(subject="admin-arch2")
    course = _publish_with_lesson(client, "Soon Archived")
    client.post(f"/api/v1/courses/{course['id']}/archive")

    make_user("learner-arch2", roles=["learner"])
    login(subject="learner-arch2")
    assert client.get("/api/v1/courses").json()["items"] == []
    assert client.get(f"/api/v1/courses/{course['id']}").status_code == 404
    assert client.get(f"/api/v1/courses/slug/{course['slug']}").status_code == 404


def test_external_link_lesson_requires_valid_url(client, make_user, login):
    make_user("trainer-link", roles=["trainer"])
    login(subject="trainer-link")
    course = _create_course(client)
    module = client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M1"}).json()

    bad = client.post(
        f"/api/v1/modules/{module['id']}/lessons",
        json={"title": "Bad", "content_type": "external_link", "content": "not-a-url"},
    )
    assert bad.status_code == 422

    missing = client.post(
        f"/api/v1/modules/{module['id']}/lessons",
        json={"title": "Missing", "content_type": "video_url"},
    )
    assert missing.status_code == 422

    good = client.post(
        f"/api/v1/modules/{module['id']}/lessons",
        json={
            "title": "Good",
            "content_type": "external_link",
            "content": "https://example.com/x",
        },
    )
    assert good.status_code == 201
    assert good.json()["content_type"] == "external_link"
    assert good.json()["content"] == "https://example.com/x"


def test_text_lesson_accepts_prose(client, make_user, login):
    make_user("trainer-text", roles=["trainer"])
    login(subject="trainer-text")
    course = _create_course(client)
    module = client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M1"}).json()
    response = client.post(
        f"/api/v1/modules/{module['id']}/lessons",
        json={"title": "Prose", "description": "Overview", "content": "Read the policy."},
    )
    assert response.status_code == 201
    assert response.json()["description"] == "Overview"


def test_update_lesson_to_link_without_url_rejected(client, make_user, login):
    make_user("trainer-upd", roles=["trainer"])
    login(subject="trainer-upd")
    course = _create_course(client)
    module = client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M1"}).json()
    lesson = client.post(
        f"/api/v1/modules/{module['id']}/lessons", json={"title": "L1", "content": "Prose"}
    ).json()
    response = client.patch(f"/api/v1/lessons/{lesson['id']}", json={"content_type": "video_url"})
    assert response.status_code == 422


def test_course_delete_cascades_tags(db_session):
    from app.modules.courses.models import Course, CourseTag

    course = Course(title="Cascade", slug="cascade", status="draft")
    db_session.add(course)
    db_session.flush()
    db_session.add(CourseTag(course_id=course.id, tag="a"))
    db_session.add(CourseTag(course_id=course.id, tag="b"))
    db_session.commit()

    db_session.delete(course)
    db_session.commit()
    assert db_session.execute(select(CourseTag)).scalars().all() == []


def test_duplicate_tag_per_course_rejected(db_session):
    from app.modules.courses.models import Course, CourseTag

    course = Course(title="Dup", slug="dup", status="draft")
    db_session.add(course)
    db_session.flush()
    db_session.add(CourseTag(course_id=course.id, tag="x"))
    db_session.add(CourseTag(course_id=course.id, tag="x"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
