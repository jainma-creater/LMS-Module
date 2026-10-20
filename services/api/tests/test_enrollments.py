"""Enrollment and assignment tests: authorization, integrity, and views."""

from datetime import UTC, datetime, timedelta


def _publish_course(client, title="Assignable Course") -> dict:
    course = client.post("/api/v1/courses", json={"title": title}).json()
    module = client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M1"}).json()
    client.post(f"/api/v1/modules/{module['id']}/lessons", json={"title": "L1"})
    client.post(f"/api/v1/courses/{course['id']}/publish")
    return course


def test_assignment_requires_authentication(deny_client):
    response = deny_client.post(
        "/api/v1/courses/00000000-0000-4000-8000-000000000000/enrollments",
        json={"learner_id": "00000000-0000-4000-8000-000000000001"},
    )
    assert response.status_code == 401


def test_learner_cannot_assign(client, make_user, login):
    learner = make_user("learner-a", roles=["learner"])
    login(subject="learner-a")
    response = client.post(
        "/api/v1/courses/00000000-0000-4000-8000-000000000000/enrollments",
        json={"learner_id": str(learner.id)},
    )
    assert response.status_code == 403


def test_admin_assigns_learner(client, make_user, login):
    learner = make_user("learner-b", roles=["learner"])
    make_user("admin-x", roles=["learning_admin"])
    login(subject="admin-x")
    course = _publish_course(client)

    response = client.post(
        f"/api/v1/courses/{course['id']}/enrollments",
        json={"learner_id": str(learner.id)},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["learner_id"] == str(learner.id)
    assert body["status"] == "assigned"
    assert body["overdue"] is False


def test_duplicate_active_enrollment_conflicts(client, make_user, login):
    learner = make_user("learner-c", roles=["learner"])
    make_user("admin-y", roles=["learning_admin"])
    login(subject="admin-y")
    course = _publish_course(client, "Dup Course")
    body = {"learner_id": str(learner.id)}
    first = client.post(f"/api/v1/courses/{course['id']}/enrollments", json=body)
    assert first.status_code == 201
    second = client.post(f"/api/v1/courses/{course['id']}/enrollments", json=body)
    assert second.status_code == 409


def test_cannot_enroll_in_unpublished_course(client, make_user, login):
    learner = make_user("learner-d", roles=["learner"])
    make_user("admin-z", roles=["learning_admin"])
    login(subject="admin-z")
    course = client.post("/api/v1/courses", json={"title": "Draft Only"}).json()
    response = client.post(
        f"/api/v1/courses/{course['id']}/enrollments",
        json={"learner_id": str(learner.id)},
    )
    assert response.status_code == 404


def test_cannot_enroll_unknown_learner(client, make_user, login):
    make_user("admin-w", roles=["learning_admin"])
    login(subject="admin-w")
    course = _publish_course(client, "Unknown Learner Course")
    response = client.post(
        f"/api/v1/courses/{course['id']}/enrollments",
        json={"learner_id": "00000000-0000-4000-8000-000000000099"},
    )
    assert response.status_code == 404


def test_my_learning_returns_course_and_progress(client, make_user, login):
    learner = make_user("learner-e", roles=["learner"])
    make_user("admin-v", roles=["learning_admin"])
    login(subject="admin-v")
    course = _publish_course(client, "Learning View Course")
    client.post(f"/api/v1/courses/{course['id']}/enrollments", json={"learner_id": str(learner.id)})

    login(subject="learner-e")
    response = client.get("/api/v1/me/learning")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["course"]["id"] == course["id"]
    assert items[0]["progress"]["percent"] == 0


def test_overdue_flag_for_past_due_date(client, make_user, login):
    learner = make_user("learner-e2", roles=["learner"])
    make_user("admin-v2", roles=["learning_admin"])
    login(subject="admin-v2")
    course = _publish_course(client, "Overdue Course")
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    created = client.post(
        f"/api/v1/courses/{course['id']}/enrollments",
        json={"learner_id": str(learner.id), "due_at": past},
    ).json()
    assert created["overdue"] is True


def test_enrollment_visibility(client, make_user, login):
    learner = make_user("learner-e2b", roles=["learner"])
    make_user("learner-f", roles=["learner"])
    make_user("admin-v2b", roles=["learning_admin"])
    login(subject="admin-v2b")
    course = _publish_course(client, "Visibility Course")
    enrollment = client.post(
        f"/api/v1/courses/{course['id']}/enrollments",
        json={"learner_id": str(learner.id)},
    ).json()

    login(subject="learner-e2b")
    assert client.get(f"/api/v1/enrollments/{enrollment['id']}").status_code == 200

    login(subject="learner-f")
    assert client.get(f"/api/v1/enrollments/{enrollment['id']}").status_code == 403

    login(subject="admin-v2b")
    assert client.get(f"/api/v1/enrollments/{enrollment['id']}").status_code == 200


def test_update_due_date(client, make_user, login):
    learner = make_user("learner-g", roles=["learner"])
    make_user("admin-u", roles=["learning_admin"])
    login(subject="admin-u")
    course = _publish_course(client, "Due Date Course")
    enrollment = client.post(
        f"/api/v1/courses/{course['id']}/enrollments",
        json={"learner_id": str(learner.id)},
    ).json()
    future = (datetime.now(UTC) + timedelta(days=5)).isoformat()
    response = client.patch(f"/api/v1/enrollments/{enrollment['id']}", json={"due_at": future})
    assert response.status_code == 200
    assert response.json()["due_at"] is not None


def _course_with_one_lesson(client, title):
    course = client.post("/api/v1/courses", json={"title": title}).json()
    module = client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M1"}).json()
    lesson = client.post(
        f"/api/v1/modules/{module['id']}/lessons", json={"title": "L1"}
    ).json()
    client.post(f"/api/v1/courses/{course['id']}/publish")
    return course, lesson


def test_my_learning_reports_progress_per_course(client, make_user, login):
    """Batch path: each enrolled course gets its own progress, not another's."""
    learner = make_user("learner-batch", roles=["learner"])
    make_user("admin-batch", roles=["learning_admin"])
    login(subject="admin-batch")
    done_course, done_lesson = _course_with_one_lesson(client, "Batch Done")
    fresh_course, _ = _course_with_one_lesson(client, "Batch Fresh")
    for course in (done_course, fresh_course):
        response = client.post(
            f"/api/v1/courses/{course['id']}/enrollments",
            json={"learner_id": str(learner.id)},
        )
        assert response.status_code == 201

    login(subject="learner-batch")
    client.put(f"/api/v1/lessons/{done_lesson['id']}/progress", json={"status": "completed"})

    items = {item["course"]["id"]: item for item in client.get("/api/v1/me/learning").json()}
    assert set(items) == {done_course["id"], fresh_course["id"]}
    assert items[done_course["id"]]["progress"] == {
        "required_lessons": 1,
        "completed_lessons": 1,
        "percent": 100,
        "is_complete": True,
    }
    assert items[fresh_course["id"]]["progress"] == {
        "required_lessons": 1,
        "completed_lessons": 0,
        "percent": 0,
        "is_complete": False,
    }

