"""Assessment tests: authoring, answer-key secrecy, server-side scoring."""

import uuid

from sqlalchemy import select

from app.modules.audit.models import AuditEvent


def _published_course_with_lesson(client, title="Assess Course"):
    course = client.post("/api/v1/courses", json={"title": title}).json()
    module = client.post(f"/api/v1/courses/{course['id']}/modules", json={"title": "M1"}).json()
    lesson = client.post(f"/api/v1/modules/{module['id']}/lessons", json={"title": "L1"}).json()
    client.post(f"/api/v1/courses/{course['id']}/publish")
    return course, module, lesson


def _single_choice_question(client, quiz_id, correct="a"):
    options = [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong"}]
    return client.post(
        f"/api/v1/quizzes/{quiz_id}/questions",
        json={
            "question_type": "single_choice",
            "prompt": "Pick one",
            "options": options,
            "answer_key": [correct],
            "explanation": "Because.",
        },
    )


def _setup_quiz(client, *, pass_score=70, attempt_limit=None, questions=1):
    course, module, lesson = _published_course_with_lesson(client)
    quiz = client.post(
        "/api/v1/quizzes",
        json={
            "title": "Quiz",
            "course_id": course["id"],
            "pass_score": pass_score,
            "attempt_limit": attempt_limit,
        },
    ).json()
    for _ in range(questions):
        _single_choice_question(client, quiz["id"])
    client.post(f"/api/v1/quizzes/{quiz['id']}/publish")
    return course, quiz


def _enroll(client, course_id, learner_id):
    return client.post(
        f"/api/v1/courses/{course_id}/enrollments", json={"learner_id": str(learner_id)}
    ).json()


# --------------------------------------------------------------------------- #
# Deny-by-default and authorization
# --------------------------------------------------------------------------- #
def test_quiz_creation_requires_authentication(deny_client):
    response = deny_client.post("/api/v1/quizzes", json={"title": "Nope"})
    assert response.status_code == 401


def test_start_attempt_requires_authentication(deny_client):
    response = deny_client.post("/api/v1/quizzes/00000000-0000-4000-8000-000000000000/attempts")
    assert response.status_code == 401


def test_learner_cannot_create_quiz(client, make_user, login):
    make_user("learner-q", roles=["learner"])
    login(subject="learner-q")
    response = client.post("/api/v1/quizzes", json={"title": "Forbidden"})
    assert response.status_code == 403


def test_quiz_requires_scope(client, make_user, login):
    make_user("admin-q", roles=["learning_admin"])
    login(subject="admin-q")
    response = client.post("/api/v1/quizzes", json={"title": "No scope"})
    assert response.status_code == 400


def test_publish_requires_questions(client, make_user, login):
    make_user("admin-q2", roles=["learning_admin"])
    login(subject="admin-q2")
    course, _, _ = _published_course_with_lesson(client, "No Q Course")
    quiz = client.post("/api/v1/quizzes", json={"title": "Empty", "course_id": course["id"]}).json()
    response = client.post(f"/api/v1/quizzes/{quiz['id']}/publish")
    assert response.status_code == 409


def test_question_answer_key_must_reference_options(client, make_user, login):
    make_user("admin-q3", roles=["learning_admin"])
    login(subject="admin-q3")
    course, _, _ = _published_course_with_lesson(client, "Bad Key Course")
    quiz = client.post("/api/v1/quizzes", json={"title": "Bad", "course_id": course["id"]}).json()
    response = client.post(
        f"/api/v1/quizzes/{quiz['id']}/questions",
        json={
            "question_type": "single_choice",
            "prompt": "Q",
            "options": [{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
            "answer_key": ["z"],
        },
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Answer-key secrecy
# --------------------------------------------------------------------------- #
def test_learner_quiz_view_hides_answer_key(client, make_user, login):
    learner = make_user("learner-q2", roles=["learner"])
    make_user("admin-q4", roles=["learning_admin"])
    login(subject="admin-q4")
    course, quiz = _setup_quiz(client)
    _enroll(client, course["id"], learner.id)

    login(subject="learner-q2")
    detail = client.get(f"/api/v1/quizzes/{quiz['id']}")
    assert detail.status_code == 200
    question = detail.json()["questions"][0]
    assert "answer_key" not in question
    assert "explanation" not in question


def test_author_quiz_view_includes_answer_key(client, make_user, login):
    make_user("admin-q5", roles=["learning_admin"])
    login(subject="admin-q5")
    course, quiz = _setup_quiz(client, questions=1)
    detail = client.get(f"/api/v1/quizzes/{quiz['id']}").json()
    assert detail["questions"][0]["answer_key"] == ["a"]


def test_start_attempt_hides_answer_key(client, make_user, login):
    learner = make_user("learner-q3", roles=["learner"])
    make_user("admin-q6", roles=["learning_admin"])
    login(subject="admin-q6")
    course, quiz = _setup_quiz(client)
    _enroll(client, course["id"], learner.id)

    login(subject="learner-q3")
    started = client.post(f"/api/v1/quizzes/{quiz['id']}/attempts")
    assert started.status_code == 201
    assert "answer_key" not in started.json()["questions"][0]


# --------------------------------------------------------------------------- #
# Attempting and scoring
# --------------------------------------------------------------------------- #
def test_correct_answers_pass(client, make_user, login):
    learner = make_user("learner-q4", roles=["learner"])
    make_user("admin-q7", roles=["learning_admin"])
    login(subject="admin-q7")
    course, quiz = _setup_quiz(client, questions=2)
    _enroll(client, course["id"], learner.id)

    login(subject="learner-q4")
    attempt = client.post(f"/api/v1/quizzes/{quiz['id']}/attempts").json()
    answers = [{"question_id": q["id"], "selected": ["a"]} for q in attempt["questions"]]
    result = client.post(
        f"/api/v1/attempts/{attempt['attempt_id']}/submit", json={"answers": answers}
    )
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["score"] == 100
    assert body["passed"] is True
    assert all(item["is_correct"] for item in body["results"])


def test_wrong_answers_fail(client, make_user, login):
    learner = make_user("learner-q5", roles=["learner"])
    make_user("admin-q8", roles=["learning_admin"])
    login(subject="admin-q8")
    course, quiz = _setup_quiz(client, questions=2)
    _enroll(client, course["id"], learner.id)

    login(subject="learner-q5")
    attempt = client.post(f"/api/v1/quizzes/{quiz['id']}/attempts").json()
    answers = [{"question_id": q["id"], "selected": ["b"]} for q in attempt["questions"]]
    result = client.post(
        f"/api/v1/attempts/{attempt['attempt_id']}/submit", json={"answers": answers}
    ).json()
    assert result["score"] == 0
    assert result["passed"] is False


def test_partial_score_threshold(client, make_user, login):
    learner = make_user("learner-q6", roles=["learner"])
    make_user("admin-q9", roles=["learning_admin"])
    login(subject="admin-q9")
    course, quiz = _setup_quiz(client, pass_score=70, questions=2)
    _enroll(client, course["id"], learner.id)

    login(subject="learner-q6")
    attempt = client.post(f"/api/v1/quizzes/{quiz['id']}/attempts").json()
    answers = [
        {"question_id": attempt["questions"][0]["id"], "selected": ["a"]},
        {"question_id": attempt["questions"][1]["id"], "selected": ["b"]},
    ]
    result = client.post(
        f"/api/v1/attempts/{attempt['attempt_id']}/submit", json={"answers": answers}
    ).json()
    assert result["score"] == 50
    assert result["passed"] is False


def test_attempt_ownership_enforced(client, make_user, login):
    learner_a = make_user("learner-q7", roles=["learner"])
    make_user("learner-q8", roles=["learner"])
    make_user("admin-q10", roles=["learning_admin"])
    login(subject="admin-q10")
    course, quiz = _setup_quiz(client)
    _enroll(client, course["id"], learner_a.id)

    login(subject="learner-q7")
    attempt = client.post(f"/api/v1/quizzes/{quiz['id']}/attempts").json()

    login(subject="learner-q8")
    response = client.post(f"/api/v1/attempts/{attempt['attempt_id']}/submit", json={"answers": []})
    assert response.status_code == 404


def test_attempt_limit_enforced(client, make_user, login):
    learner = make_user("learner-q9", roles=["learner"])
    make_user("admin-q11", roles=["learning_admin"])
    login(subject="admin-q11")
    course, quiz = _setup_quiz(client, attempt_limit=1)
    _enroll(client, course["id"], learner.id)

    login(subject="learner-q9")
    attempt = client.post(f"/api/v1/quizzes/{quiz['id']}/attempts").json()
    client.post(f"/api/v1/attempts/{attempt['attempt_id']}/submit", json={"answers": []})
    second = client.post(f"/api/v1/quizzes/{quiz['id']}/attempts")
    assert second.status_code == 409


def test_multiple_choice_requires_exact_set(client, make_user, login):
    learner = make_user("learner-q10", roles=["learner"])
    make_user("admin-q12", roles=["learning_admin"])
    login(subject="admin-q12")
    course, _, _ = _published_course_with_lesson(client, "MC Course")
    quiz = client.post("/api/v1/quizzes", json={"title": "MC", "course_id": course["id"]}).json()
    client.post(
        f"/api/v1/quizzes/{quiz['id']}/questions",
        json={
            "question_type": "multiple_choice",
            "prompt": "Pick two",
            "options": [
                {"id": "a", "text": "A"},
                {"id": "b", "text": "B"},
                {"id": "c", "text": "C"},
            ],
            "answer_key": ["a", "b"],
        },
    )
    client.post(f"/api/v1/quizzes/{quiz['id']}/publish")
    _enroll(client, course["id"], learner.id)

    login(subject="learner-q10")
    attempt = client.post(f"/api/v1/quizzes/{quiz['id']}/attempts").json()
    partial = client.post(
        f"/api/v1/attempts/{attempt['attempt_id']}/submit",
        json={"answers": [{"question_id": attempt["questions"][0]["id"], "selected": ["a"]}]},
    ).json()
    assert partial["score"] == 0

    attempt2 = client.post(f"/api/v1/quizzes/{quiz['id']}/attempts").json()
    full = client.post(
        f"/api/v1/attempts/{attempt2['attempt_id']}/submit",
        json={"answers": [{"question_id": attempt2["questions"][0]["id"], "selected": ["a", "b"]}]},
    ).json()
    assert full["score"] == 100


def test_cannot_attempt_unpublished_quiz(client, make_user, login):
    learner = make_user("learner-q11", roles=["learner"])
    make_user("admin-q13", roles=["learning_admin"])
    login(subject="admin-q13")
    course, _, _ = _published_course_with_lesson(client, "Draft Quiz Course")
    quiz = client.post("/api/v1/quizzes", json={"title": "Draft", "course_id": course["id"]}).json()
    _single_choice_question(client, quiz["id"])
    _enroll(client, course["id"], learner.id)

    login(subject="learner-q11")
    response = client.post(f"/api/v1/quizzes/{quiz['id']}/attempts")
    assert response.status_code == 404


def test_attempt_requires_enrollment(client, make_user, login):
    make_user("learner-q12", roles=["learner"])
    make_user("admin-q14", roles=["learning_admin"])
    login(subject="admin-q14")
    course, quiz = _setup_quiz(client, pass_score=70)

    login(subject="learner-q12")
    response = client.post(f"/api/v1/quizzes/{quiz['id']}/attempts")
    assert response.status_code == 409


def test_quiz_publication_is_audited(client, make_user, login, db_session):
    make_user("admin-q15", roles=["learning_admin"])
    login(subject="admin-q15")
    _setup_quiz(client)
    events = list(db_session.execute(select(AuditEvent)).scalars())
    actions = {event.action for event in events}
    assert {"quiz.created", "question.created", "quiz.published"}.issubset(actions)


def test_results_list_own_attempts(client, make_user, login):
    learner = make_user("learner-q13", roles=["learner"])
    make_user("admin-q16", roles=["learning_admin"])
    login(subject="admin-q16")
    course, quiz = _setup_quiz(client, questions=1)
    _enroll(client, course["id"], learner.id)

    login(subject="learner-q13")
    attempt = client.post(f"/api/v1/quizzes/{quiz['id']}/attempts").json()
    client.post(f"/api/v1/attempts/{attempt['attempt_id']}/submit", json={"answers": []})
    results = client.get(f"/api/v1/quizzes/{quiz['id']}/results").json()
    assert len(results) == 1
    assert results[0]["id"] == attempt["attempt_id"]
    assert "answer_key" not in str(results)


def test_unknown_quiz_returns_404(client, make_user, login):
    make_user("admin-q17", roles=["learning_admin"])
    login(subject="admin-q17")
    missing = uuid.uuid4()
    assert client.get(f"/api/v1/quizzes/{missing}").status_code == 404
