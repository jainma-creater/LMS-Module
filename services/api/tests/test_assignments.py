"""Course assignments and group course assignments tests.

Covers: individual and group assignments, due dates, duplicate prevention,
cancellation, group membership changes, and authorization.
"""

import uuid
from datetime import UTC, datetime, timedelta


def _publish_course(client) -> dict:
    """Create a published course as learning_admin, return course data."""
    # This function should be called when authenticated as learning_admin or system_admin
    course = client.post(
        "/api/v1/courses", json={"title": "Assignable Course", "difficulty_level": "beginner"}
    ).json()
    module = client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M1"}).json()
    client.post(f"/api/v1/modules/{module['id']}/lessons", json={"title": "L1"})
    client.post(f"/api/v1/courses/{course['id']}/publish")
    return course


def _create_learner(client, **overrides) -> dict:
    payload = {
        "employee_id": f"EMP-{uuid.uuid4().hex[:8]}",
        "first_name": "John",
        "last_name": "Doe",
        "email": f"john.doe+{uuid.uuid4().hex[:8]}@example.com",
        "status": "active",
        **overrides,
    }
    response = client.post("/api/v1/learners", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def _create_group(client, **overrides) -> dict:
    payload = {
        "name": f"Group-{uuid.uuid4().hex[:8]}",
        "description": "Test group",
        "kind": "team",
        "status": "active",
        **overrides,
    }
    response = client.post("/api/v1/learning-groups", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------- #
# Deny-by-default
# --------------------------------------------------------------------------- #
def test_assignments_list_requires_authentication(deny_client):
    assert deny_client.get("/api/v1/assignments").status_code == 401


def test_create_assignment_requires_authentication(deny_client):
    assert (
        deny_client.post(
            "/api/v1/courses/00000000-0000-4000-8000-000000000000/assignments", json={}
        ).status_code
        == 401
    )


def test_group_assignments_list_requires_authentication(deny_client):
    assert deny_client.get("/api/v1/group-assignments").status_code == 401


def test_create_group_assignment_requires_authentication(deny_client):
    assert (
        deny_client.post(
            "/api/v1/courses/00000000-0000-4000-8000-000000000000/group-assignments", json={}
        ).status_code
        == 401
    )


# --------------------------------------------------------------------------- #
# Authorization
# --------------------------------------------------------------------------- #
def test_learner_cannot_create_assignment(client, make_user, login):
    # First create a course and learner as admin
    make_user("admin-setup", roles=["learning_admin"])
    login(subject="admin-setup")
    course = _publish_course(client)
    course_id = course["id"]
    learner = _create_learner(client)
    learner_id = learner["id"]
    # Now test as learner
    make_user("learner-a", roles=["learner"])
    login(subject="learner-a")
    assert (
        client.post(
            f"/api/v1/courses/{course_id}/assignments", json={"learner_id": learner_id}
        ).status_code
        == 403
    )


def test_learner_cannot_create_group_assignment(client, make_user, login):
    make_user("admin-setup", roles=["learning_admin"])
    login(subject="admin-setup")
    course = _publish_course(client)
    group = _create_group(client)
    course_id = course["id"]
    make_user("learner-b", roles=["learner"])
    login(subject="learner-b")
    assert (
        client.post(
            f"/api/v1/courses/{course_id}/group-assignments", json={"group_id": group["id"]}
        ).status_code
        == 403
    )


def test_learning_admin_can_assign(client, make_user, login):
    make_user("admin-a", roles=["learning_admin"])
    login(subject="admin-a")
    course = _publish_course(client)
    learner = _create_learner(client)
    r = client.post(
        f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner["id"]}
    )
    assert r.status_code == 201, r.text
    assert r.json()["source"] == "individual"


def test_system_admin_can_assign(client, make_user, login):
    make_user("sys-a", roles=["system_admin"])
    login(subject="sys-a")
    course = _publish_course(client)
    learner = _create_learner(client)
    assert (
        client.post(
            f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner["id"]}
        ).status_code
        == 201
    )


def test_learner_cannot_cancel_assignment(client, make_user, login):
    make_user("learner-c", roles=["learner"])
    login(subject="learner-c")
    make_user("admin-c", roles=["learning_admin"])
    login(subject="admin-c")
    course = _publish_course(client)
    learner = _create_learner(client)
    assign = client.post(
        f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner["id"]}
    ).json()
    login(subject="learner-c")
    assert client.post(f"/api/v1/assignments/{assign['id']}/cancel").status_code == 403


# --------------------------------------------------------------------------- #
# Individual assignments
# --------------------------------------------------------------------------- #
def test_create_individual_assignment(client, make_user, login):
    make_user("admin-1", roles=["learning_admin"])
    login(subject="admin-1")
    course = _publish_course(client)
    learner = _create_learner(client)
    due = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    r = client.post(
        f"/api/v1/courses/{course['id']}/assignments",
        json={"learner_id": learner["id"], "due_at": due},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["learner_id"] == learner["id"]
    assert body["course_id"] == course["id"]
    assert body["source"] == "individual"
    assert body["status"] == "active"
    assert body["derived_status"] in ("assigned", "awaiting_account")


def test_create_assignment_with_due_date(client, make_user, login):
    make_user("admin-2", roles=["learning_admin"])
    login(subject="admin-2")
    course = _publish_course(client)
    learner = _create_learner(client)
    due = (datetime.now(UTC) + timedelta(days=14)).isoformat()
    r = client.post(
        f"/api/v1/courses/{course['id']}/assignments",
        json={"learner_id": learner["id"], "due_at": due},
    )
    assert r.status_code == 201
    assert r.json()["due_at"] is not None


def test_create_assignment_prevents_duplicate(client, make_user, login):
    make_user("admin-3", roles=["learning_admin"])
    login(subject="admin-3")
    course = _publish_course(client)
    learner = _create_learner(client)
    client.post(f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner["id"]})
    r = client.post(
        f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner["id"]}
    )
    assert r.status_code == 409


def test_cannot_assign_to_unpublished_course(client, make_user, login):
    make_user("admin-4", roles=["learning_admin"])
    login(subject="admin-4")
    course = client.post(
        "/api/v1/courses", json={"title": "Draft Course", "difficulty_level": "beginner"}
    ).json()
    learner = _create_learner(client)
    r = client.post(
        f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner["id"]}
    )
    assert r.status_code == 409


def test_cannot_assign_to_archived_course(client, make_user, login):
    make_user("admin-5", roles=["learning_admin"])
    login(subject="admin-5")
    course = _publish_course(client)
    client.post(f"/api/v1/courses/{course['id']}/archive")
    learner = _create_learner(client)
    r = client.post(
        f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner["id"]}
    )
    assert r.status_code == 409


def test_cannot_assign_inactive_learner(client, make_user, login):
    make_user("admin-6", roles=["learning_admin"])
    login(subject="admin-6")
    course = _publish_course(client)
    learner = _create_learner(client, status="inactive")
    r = client.post(
        f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner["id"]}
    )
    assert r.status_code == 409


def test_assignment_due_date_update(client, make_user, login):
    make_user("admin-7", roles=["learning_admin"])
    login(subject="admin-7")
    course = _publish_course(client)
    learner = _create_learner(client)
    assign = client.post(
        f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner["id"]}
    ).json()
    new_due = (datetime.now(UTC) + timedelta(days=60)).isoformat()
    r = client.patch(f"/api/v1/assignments/{assign['id']}", json={"due_at": new_due})
    assert r.status_code == 200
    assert r.json()["due_at"] is not None


def test_cancel_assignment_withdraws_enrollment(client, make_user, login, db_session):
    make_user("admin-8", roles=["learning_admin"])
    login(subject="admin-8")
    course = _publish_course(client)
    learner = _create_learner(client)
    assign = client.post(
        f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner["id"]}
    ).json()
    # Need a linked user for enrollment
    from app.modules.users.models import User, UserStatus

    user = User(
        external_identity_id=f"ext-{uuid.uuid4().hex[:8]}",
        email="e@e.com",
        display_name="U",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()
    client.patch(f"/api/v1/learners/{learner['id']}", json={"user_id": str(user.id)})
    # Re-fetch assignment to get enrollment_id
    assign = client.get(f"/api/v1/assignments/{assign['id']}").json()
    # Now cancel
    r = client.post(f"/api/v1/assignments/{assign['id']}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    # Verify enrollment was withdrawn
    from app.modules.enrollments import repository as enroll_repo

    enrollment = enroll_repo.get_enrollment(db_session, uuid.UUID(assign["enrollment_id"]))
    assert enrollment is not None
    assert enrollment.status == "withdrawn"


def test_cancel_already_cancelled_assignment(client, make_user, login):
    make_user("admin-9", roles=["learning_admin"])
    login(subject="admin-9")
    course = _publish_course(client)
    learner = _create_learner(client)
    assign = client.post(
        f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner["id"]}
    ).json()
    client.post(f"/api/v1/assignments/{assign['id']}/cancel")
    r = client.post(f"/api/v1/assignments/{assign['id']}/cancel")
    assert r.status_code == 409


def test_get_assignment_detail(client, make_user, login):
    make_user("admin-10", roles=["learning_admin"])
    login(subject="admin-10")
    course = _publish_course(client)
    learner = _create_learner(client)
    assign = client.post(
        f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner["id"]}
    ).json()
    r = client.get(f"/api/v1/assignments/{assign['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == assign["id"]
    assert "enrollment" in r.json()
    assert "progress" in r.json()


def test_list_assignments_pagination(client, make_user, login):
    make_user("admin-pager", roles=["learning_admin"])
    login(subject="admin-pager")
    course = _publish_course(client)
    for i in range(5):
        learner = _create_learner(client, employee_id=f"EMP-PG-{i:02d}", email=f"pg{i}@ex.com")
        client.post(
            f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner["id"]}
        )
    r = client.get("/api/v1/assignments", params={"limit": 2, "offset": 0})
    assert r.status_code == 200
    assert len(r.json()["items"]) == 2
    assert r.json()["total"] >= 5


def test_list_assignments_filter_by_derived_status(client, make_user, login):
    make_user("admin-filter", roles=["learning_admin"])
    login(subject="admin-filter")
    course = _publish_course(client)
    learner = _create_learner(client)
    assign = client.post(
        f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner["id"]}
    ).json()
    # Without linked user, should be awaiting_account
    r = client.get("/api/v1/assignments", params={"derived": "awaiting_account"})
    assert r.status_code == 200
    assert any(a["id"] == assign["id"] for a in r.json()["items"])


def test_list_assignments_filter_overdue(client, make_user, login):
    make_user("admin-overdue", roles=["learning_admin"])
    login(subject="admin-overdue")
    course = _publish_course(client)
    learner = _create_learner(client)
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    assign = client.post(
        f"/api/v1/courses/{course['id']}/assignments",
        json={"learner_id": learner["id"], "due_at": past},
    ).json()
    r = client.get("/api/v1/assignments", params={"overdue": "true"})
    assert r.status_code == 200
    assert any(a["id"] == assign["id"] for a in r.json()["items"])


# --------------------------------------------------------------------------- #
# Group assignments
# --------------------------------------------------------------------------- #
def test_create_group_assignment(client, make_user, login):
    make_user("admin-g1", roles=["learning_admin"])
    login(subject="admin-g1")
    course = _publish_course(client)
    group = _create_group(client)
    due = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    r = client.post(
        f"/api/v1/courses/{course['id']}/group-assignments",
        json={"group_id": group["id"], "due_at": due},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["group_assignment"]["group_id"] == group["id"]
    assert body["group_assignment"]["course_id"] == course["id"]
    assert body["group_assignment"]["status"] == "active"
    assert body["created"] >= 0


def test_create_group_assignment_prevents_duplicate(client, make_user, login):
    make_user("admin-g2", roles=["learning_admin"])
    login(subject="admin-g2")
    course = _publish_course(client)
    group = _create_group(client)
    client.post(f"/api/v1/courses/{course['id']}/group-assignments", json={"group_id": group["id"]})
    r = client.post(
        f"/api/v1/courses/{course['id']}/group-assignments", json={"group_id": group["id"]}
    )
    assert r.status_code == 409


def test_cannot_group_assign_unpublished_course(client, make_user, login):
    make_user("admin-g3", roles=["learning_admin"])
    login(subject="admin-g3")
    course = client.post(
        "/api/v1/courses", json={"title": "Draft Course", "difficulty_level": "beginner"}
    ).json()
    group = _create_group(client)
    r = client.post(
        f"/api/v1/courses/{course['id']}/group-assignments", json={"group_id": group["id"]}
    )
    assert r.status_code == 409


def test_cannot_group_assign_inactive_group(client, make_user, login):
    make_user("admin-g4", roles=["learning_admin"])
    login(subject="admin-g4")
    course = _publish_course(client)
    group = _create_group(client, status="inactive")
    r = client.post(
        f"/api/v1/courses/{course['id']}/group-assignments", json={"group_id": group["id"]}
    )
    assert r.status_code == 409


def test_group_assignment_expands_to_members(client, make_user, login):
    make_user("admin-g5", roles=["learning_admin"])
    login(subject="admin-g5")
    course = _publish_course(client)
    group = _create_group(client)
    learner = _create_learner(client)
    client.post(
        f"/api/v1/learning-groups/{group['id']}/members", json={"learner_id": learner["id"]}
    )
    r = client.post(
        f"/api/v1/courses/{course['id']}/group-assignments", json={"group_id": group["id"]}
    )
    assert r.status_code == 201
    assert r.json()["created"] >= 1


def test_group_assignment_skips_existing_assignments(client, make_user, login):
    make_user("admin-g6", roles=["learning_admin"])
    login(subject="admin-g6")
    course = _publish_course(client)
    group = _create_group(client)
    # Learner with existing assignment
    learner1 = _create_learner(client)
    client.post(
        f"/api/v1/learning-groups/{group['id']}/members", json={"learner_id": learner1["id"]}
    )
    client.post(f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner1["id"]})
    # Active learner without assignment
    learner2 = _create_learner(client)
    client.post(
        f"/api/v1/learning-groups/{group['id']}/members", json={"learner_id": learner2["id"]}
    )

    r = client.post(
        f"/api/v1/courses/{course['id']}/group-assignments", json={"group_id": group["id"]}
    )
    assert r.status_code == 201
    assert r.json()["created"] == 1  # only learner2
    assert r.json()["skipped_existing"] == 1  # learner1


def test_cancel_group_assignment_cancels_member_assignments(client, make_user, login):
    make_user("admin-g7", roles=["learning_admin"])
    login(subject="admin-g7")
    course = _publish_course(client)
    group = _create_group(client)
    learner = _create_learner(client)
    client.post(
        f"/api/v1/learning-groups/{group['id']}/members", json={"learner_id": learner["id"]}
    )
    grp_assign = client.post(
        f"/api/v1/courses/{course['id']}/group-assignments", json={"group_id": group["id"]}
    ).json()
    grp_assign_id = grp_assign["group_assignment"]["id"]
    # Cancel group assignment
    r = client.post(f"/api/v1/group-assignments/{grp_assign_id}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    # Verify member assignment was cancelled
    response = client.get(
        "/api/v1/assignments", params={"learner_id": learner["id"], "course_id": course["id"]}
    )
    items = response.json()["items"]
    cancelled = [a for a in items if a["status"] == "cancelled"]
    assert len(cancelled) >= 1


def test_cancel_group_assignment_does_not_affect_individual_assignments(client, make_user, login):
    make_user("admin-g8", roles=["learning_admin"])
    login(subject="admin-g8")
    course = _publish_course(client)
    group = _create_group(client)
    learner = _create_learner(client)
    # Individual assignment first
    client.post(f"/api/v1/courses/{course['id']}/assignments", json={"learner_id": learner["id"]})
    # Then group assignment (should skip existing)
    client.post(
        f"/api/v1/learning-groups/{group['id']}/members", json={"learner_id": learner["id"]}
    )
    grp_assign = client.post(
        f"/api/v1/courses/{course['id']}/group-assignments", json={"group_id": group["id"]}
    ).json()
    grp_assign_id = grp_assign["group_assignment"]["id"]
    # Cancel group assignment
    client.post(f"/api/v1/group-assignments/{grp_assign_id}/cancel")
    # Individual assignment should remain active
    response = client.get(
        "/api/v1/assignments", params={"learner_id": learner["id"], "course_id": course["id"]}
    )
    items = response.json()["items"]
    active = [a for a in items if a["status"] == "active" and a["source"] == "individual"]
    assert len(active) >= 1


def test_list_group_assignments_pagination(client, make_user, login):
    make_user("admin-gp", roles=["learning_admin"])
    login(subject="admin-gp")
    course = _publish_course(client)
    for i in range(3):
        group = _create_group(client, name=f"Group-{i}")
        client.post(
            f"/api/v1/courses/{course['id']}/group-assignments", json={"group_id": group["id"]}
        )
    r = client.get("/api/v1/group-assignments", params={"limit": 2, "offset": 0})
    assert r.status_code == 200
    assert len(r.json()["items"]) == 2
    assert r.json()["total"] >= 3


def test_learner_cannot_view_assignments(client, make_user, login):
    make_user("learner-v", roles=["learner"])
    login(subject="learner-v")
    assert client.get("/api/v1/assignments").status_code == 403
    assert client.get("/api/v1/group-assignments").status_code == 403
