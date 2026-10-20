"""Progress and completion tests: transitions, server-side completion, audit."""

from sqlalchemy import select

from app.modules.audit.models import AuditEvent


def _course_with_lessons(client, required=(True, True), extra_optional=False):
    course = client.post("/api/v1/courses", json={"title": "Progress Course"}).json()
    module = client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M1"}).json()
    lessons = []
    for index, is_required in enumerate(required):
        lesson = client.post(
            f"/api/v1/modules/{module['id']}/lessons",
            json={"title": f"L{index}", "is_required": is_required},
        ).json()
        lessons.append(lesson)
    if extra_optional:
        lessons.append(
            client.post(
                f"/api/v1/modules/{module['id']}/lessons",
                json={"title": "Optional", "is_required": False},
            ).json()
        )
    client.post(f"/api/v1/courses/{course['id']}/publish")
    return course, lessons


def _enroll(client, course_id, learner_id):
    return client.post(
        f"/api/v1/courses/{course_id}/enrollments", json={"learner_id": str(learner_id)}
    ).json()


def test_progress_write_requires_authentication(deny_client):
    response = deny_client.put(
        "/api/v1/lessons/00000000-0000-4000-8000-000000000000/progress",
        json={"status": "completed"},
    )
    assert response.status_code == 401


def test_progress_requires_enrollment(client, make_user, login):
    make_user("admin-p", roles=["learning_admin"])
    login(subject="admin-p")
    course, lessons = _course_with_lessons(client)
    make_user("learner-p0", roles=["learner"])

    login(subject="learner-p0")
    response = client.put(
        f"/api/v1/lessons/{lessons[0]['id']}/progress", json={"status": "completed"}
    )
    assert response.status_code == 409


def test_recording_progress_starts_enrollment(client, make_user, login):
    learner = make_user("learner-p1", roles=["learner"])
    make_user("admin-p1", roles=["learning_admin"])
    login(subject="admin-p1")
    course, lessons = _course_with_lessons(client)
    enrollment = _enroll(client, course["id"], learner.id)

    login(subject="learner-p1")
    response = client.put(
        f"/api/v1/lessons/{lessons[0]['id']}/progress",
        json={"status": "in_progress", "last_position": 30},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    login(subject="admin-p1")
    updated = client.get(f"/api/v1/enrollments/{enrollment['id']}").json()
    assert updated["status"] == "in_progress"


def test_completion_recorded_once_all_required_done(client, make_user, login, db_session):
    learner = make_user("learner-p2", roles=["learner"])
    make_user("admin-p2", roles=["learning_admin"])
    login(subject="admin-p2")
    course, lessons = _course_with_lessons(client)
    _enroll(client, course["id"], learner.id)

    login(subject="learner-p2")
    for lesson in lessons:
        response = client.put(
            f"/api/v1/lessons/{lesson['id']}/progress", json={"status": "completed"}
        )
        assert response.status_code == 200

    completions = client.get("/api/v1/me/progress").json()
    assert len(completions) == 1
    assert completions[0]["course_id"] == course["id"]
    assert completions[0]["completion_rule_version"] == 1

    # Re-completing does not create a duplicate completion.
    client.put(f"/api/v1/lessons/{lessons[0]['id']}/progress", json={"status": "completed"})
    assert len(client.get("/api/v1/me/progress").json()) == 1

    completed_events = list(
        db_session.execute(
            select(AuditEvent).where(AuditEvent.action == "course.completed")
        ).scalars()
    )
    assert len(completed_events) == 1


def test_enrollment_completed_with_course(client, make_user, login):
    learner = make_user("learner-p3", roles=["learner"])
    make_user("admin-p3", roles=["learning_admin"])
    login(subject="admin-p3")
    course, lessons = _course_with_lessons(client, required=(True,))
    enrollment = _enroll(client, course["id"], learner.id)

    login(subject="learner-p3")
    client.put(f"/api/v1/lessons/{lessons[0]['id']}/progress", json={"status": "completed"})

    login(subject="admin-p3")
    detail = client.get(f"/api/v1/enrollments/{enrollment['id']}").json()
    assert detail["status"] == "completed"
    assert detail["completed_at"] is not None


def test_optional_lessons_do_not_block_completion(client, make_user, login):
    learner = make_user("learner-p4", roles=["learner"])
    make_user("admin-p4", roles=["learning_admin"])
    login(subject="admin-p4")
    course, lessons = _course_with_lessons(client, required=(True,), extra_optional=True)
    _enroll(client, course["id"], learner.id)

    login(subject="learner-p4")
    client.put(f"/api/v1/lessons/{lessons[0]['id']}/progress", json={"status": "completed"})

    progress = client.get(f"/api/v1/courses/{course['id']}/progress").json()
    assert progress["required_lessons"] == 1
    assert progress["completed_lessons"] == 1
    assert progress["percent"] == 100
    assert progress["is_complete"] is True


def test_course_progress_reports_partial(client, make_user, login):
    learner = make_user("learner-p5", roles=["learner"])
    make_user("admin-p5", roles=["learning_admin"])
    login(subject="admin-p5")
    course, lessons = _course_with_lessons(client, required=(True, True, True))
    _enroll(client, course["id"], learner.id)

    login(subject="learner-p5")
    client.put(f"/api/v1/lessons/{lessons[0]['id']}/progress", json={"status": "completed"})

    progress = client.get(f"/api/v1/courses/{course['id']}/progress").json()
    assert progress["completed_lessons"] == 1
    assert progress["percent"] == 33
    assert progress["is_complete"] is False
