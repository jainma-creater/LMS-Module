"""Comprehensive tests for AI Training Studio:

- Guided generation from topic or source document
- Video narration script, storyboard, and WebVTT captions
- Objective quiz generation and single-question regeneration
- Human-in-the-loop review (draft before publish)
- 1-click approve, publish, and assignment workflow
- Media asset serving and captions
- Authorization boundaries
"""

import uuid
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.modules.assessments.models import Quiz, QuizStatus
from app.modules.audit.models import AuditEvent
from app.modules.courses.models import Course, CourseStatus
from app.modules.training_studio import renderer_client


@pytest.fixture(autouse=True)
def fake_renderer(monkeypatch, tmp_path):
    """Stand in for the Remotion container: writes an MP4-shaped file, no TTS calls.

    Runs inside tmp_path so test artifacts never land in the shared storage volume.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(get_settings(), "gemini_api_key", None)

    def fake_post(url, json, timeout):  # noqa: A002
        target = Path("storage/videos") / f"video_{json['job_id']}.mp4"
        target.parent.mkdir(parents=True, exist_ok=True)
        # ISO BMFF header plus padding so the asset passes the size and ftyp checks.
        target.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 2048)
        return httpx.Response(200, json={"ok": True})

    monkeypatch.setattr(renderer_client.httpx, "post", fake_post)


def test_generate_requires_authentication(deny_client):
    response = deny_client.post("/api/v1/studio/generate", json={"topic": "Security"})
    assert response.status_code == 401


def test_learner_cannot_generate_training(client, make_user, login):
    make_user("learner-studio", roles=["learner"])
    login(subject="learner-studio")
    response = client.post("/api/v1/studio/generate", json={"topic": "Security"})
    assert response.status_code == 403


def test_generate_from_topic_creates_complete_draft(client, make_user, login):
    make_user("admin-studio-1", roles=["learning_admin"])
    login(subject="admin-studio-1")

    payload = {
        "topic": "Workplace Data Privacy & GDPR",
        "language": "en",
        "target_duration_minutes": 15,
        "audience": "Engineering & Product",
        "include_quiz": True,
        "include_video": True,
    }
    response = client.post("/api/v1/studio/generate", json=payload)
    assert response.status_code == 201, response.text
    job = response.json()

    assert job["status"] == "generated"
    assert job["progress_percent"] == 100
    assert job["stage"] == "complete"
    assert "Data Privacy" in job["title"]

    course_data = job["generated_course_data"]
    assert course_data is not None
    assert len(course_data["learning_objectives"]) >= 3
    assert len(course_data["key_takeaways"]) >= 2
    assert len(course_data["modules"]) >= 2

    # Verify lessons
    first_module = course_data["modules"][0]
    assert len(first_module["lessons"]) >= 2
    assert first_module["lessons"][0]["is_required"] is True

    # Verify quiz
    quiz_data = job["generated_quiz_data"]
    assert quiz_data is not None
    assert quiz_data["pass_score"] == 70
    assert len(quiz_data["questions"]) >= 3
    for q in quiz_data["questions"]:
        assert len(q["options"]) >= 2
        assert len(q["answer_key"]) >= 1
        assert len(q["explanation"]) > 5

    # Verify video storyboard and captions
    assert len(course_data["storyboard"]) >= 3
    assert "WEBVTT" in course_data["captions_vtt"]
    assert job["generated_video_asset_url"] is not None
    assert job["generated_video_duration_seconds"] > 0


def test_generate_from_uploaded_text_document(client, make_user, login):
    make_user("admin-studio-doc", roles=["learning_admin"])
    login(subject="admin-studio-doc")

    doc_content = (
        b"Incident Escalation Protocol\n\n"
        b"All critical system failures must be escalated within 15 minutes to on-call leads.\n"
        b"Never commit secrets into source control or disable access logging.\n"
    )
    files = {"file": ("escalation_guide.txt", doc_content, "text/plain")}
    data = {"topic": "Incident Escalation", "audience": "DevOps"}

    response = client.post("/api/v1/studio/generate", data=data, files=files)
    assert response.status_code == 201
    job = response.json()
    assert job["source_file_name"] == "escalation_guide.txt"
    assert "Incident Escalation" in job["title"]


def test_edit_draft_before_publishing(client, make_user, login):
    make_user("admin-studio-edit", roles=["learning_admin"])
    login(subject="admin-studio-edit")

    # Generate draft
    gen = client.post("/api/v1/studio/generate", json={"topic": "Customer Empathy"}).json()
    job_id = gen["id"]

    # Edit draft
    course_draft = gen["generated_course_data"]
    course_draft["title"] = "Advanced Customer Empathy & Active Listening"
    course_draft["short_description"] = "Updated customized description for customer support."

    patch_res = client.patch(
        f"/api/v1/studio/jobs/{job_id}",
        json={"course": course_draft},
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["title"] == "Advanced Customer Empathy & Active Listening"
    assert (
        updated["generated_course_data"]["title"] == "Advanced Customer Empathy & Active Listening"
    )


def test_regenerate_single_question(client, make_user, login):
    make_user("admin-studio-regen", roles=["learning_admin"])
    login(subject="admin-studio-regen")

    gen = client.post("/api/v1/studio/generate", json={"topic": "Anti-Bribery Standards"}).json()
    job_id = gen["id"]

    orig_q0_prompt = gen["generated_quiz_data"]["questions"][0]["prompt"]

    # Regenerate question 0
    regen_res = client.post(
        f"/api/v1/studio/jobs/{job_id}/regenerate-question",
        json={"question_index": 0, "topic_hint": "Gift Acceptance Thresholds"},
    )
    assert regen_res.status_code == 200
    new_q = regen_res.json()
    assert new_q["prompt"] != orig_q0_prompt

    # Fetch updated job and ensure question 0 changed while question 1 remained intact
    job = client.get(f"/api/v1/studio/jobs/{job_id}").json()
    assert job["generated_quiz_data"]["questions"][0]["prompt"] == new_q["prompt"]
    assert len(job["generated_quiz_data"]["questions"]) == len(
        gen["generated_quiz_data"]["questions"]
    )


def test_generated_training_is_draft_until_explicitly_published(
    client, make_user, login, db_session
):
    make_user("admin-studio-draft", roles=["learning_admin"])
    login(subject="admin-studio-draft")

    gen = client.post("/api/v1/studio/generate", json={"topic": "Unpublished Safety Guide"}).json()
    assert gen["id"] is not None

    # Check course table: no course should exist with this title yet
    courses = list(db_session.execute(select(Course).where(Course.title == gen["title"])).scalars())
    assert len(courses) == 0


def test_publish_draft_creates_course_quiz_and_group_assignment(
    client, make_user, login, db_session
):
    make_user("admin-studio-pub", roles=["learning_admin"])
    login(subject="admin-studio-pub")

    # 1. Create a learning group to assign to
    group = client.post("/api/v1/learning-groups", json={"name": "Security Champions"}).json()

    # 2. Generate training draft
    gen = client.post(
        "/api/v1/studio/generate",
        json={"topic": "Secure Coding Practices", "audience": "Software Engineers"},
    ).json()
    job_id = gen["id"]

    # 3. Approve & Publish with 1 click to group
    pub_res = client.post(
        f"/api/v1/studio/jobs/{job_id}/publish",
        json={"assign_to_group_id": group["id"], "due_days": 21},
    )
    assert pub_res.status_code == 200, pub_res.text
    result = pub_res.json()

    course_id = uuid.UUID(result["course_id"])
    course_slug = result["course_slug"]
    assert result["quiz_id"] is not None
    assert result["group_assignment_id"] is not None

    # Verify course is published
    course = db_session.get(Course, course_id)
    assert course is not None
    assert course.status == CourseStatus.PUBLISHED

    # Verify public catalog can find published course
    catalog_res = client.get(f"/api/v1/courses/slug/{course_slug}")
    assert catalog_res.status_code == 200

    # Verify quiz is published
    quiz = db_session.get(Quiz, uuid.UUID(result["quiz_id"]))
    assert quiz is not None
    assert quiz.status == QuizStatus.PUBLISHED

    # Verify audit event was emitted
    audit = db_session.execute(
        select(AuditEvent).where(
            AuditEvent.action == "training_studio.published",
            AuditEvent.target_id == str(course_id),
        )
    ).scalar_one_or_none()
    assert audit is not None


def test_video_asset_and_captions_serving(client, make_user, login):
    make_user("admin-studio-media", roles=["learning_admin"])
    login(subject="admin-studio-media")

    gen = client.post("/api/v1/studio/generate", json={"topic": "Media Serving Test"}).json()
    job_id = gen["id"]
    video_url = gen["generated_video_asset_url"]

    # Test captions endpoint
    captions_res = client.get(f"/api/v1/studio/captions/{job_id}")
    assert captions_res.status_code == 200
    assert "text/vtt" in captions_res.headers["content-type"]
    assert "WEBVTT" in captions_res.text

    # Test video asset endpoint
    video_res = client.get(video_url)
    assert video_res.status_code == 200
    assert "video/mp4" in video_res.headers["content-type"]
    assert video_res.content[4:8] == b"ftyp"


def test_failed_generation_is_persisted_and_reported(client, make_user, login, monkeypatch):
    make_user("admin-studio-fail", roles=["learning_admin"])
    login(subject="admin-studio-fail")

    from app.modules.training_studio import generator

    def boom(**_kwargs):
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(generator, "generate_course_from_source", boom)

    response = client.post("/api/v1/studio/generate", json={"topic": "Failure Path"})
    assert response.status_code == 201, response.text
    job = response.json()
    assert job["status"] == "failed"
    assert job["stage"] == "failed"
    assert "model unavailable" in job["error_message"]

    # The failure must survive a re-read, not only the response body.
    reread = client.get(f"/api/v1/studio/jobs/{job['id']}")
    assert reread.status_code == 200
    assert reread.json()["status"] == "failed"


def test_media_endpoints_enforce_permissions(client, deny_client, make_user, login):
    # Anonymous callers are denied on both media endpoints.
    fake_id = "00000000-0000-0000-0000-000000000001"
    assert deny_client.get(f"/api/v1/studio/captions/{fake_id}").status_code == 401
    assert deny_client.get("/api/v1/studio/video-asset/video_x.mp4").status_code == 401

    # Learners may watch rendered video but may not read draft captions.
    make_user("admin-studio-gate", roles=["learning_admin"])
    login(subject="admin-studio-gate")
    gen = client.post("/api/v1/studio/generate", json={"topic": "Gate Check"}).json()
    video_path = gen["generated_video_asset_url"]

    make_user("learner-studio-gate", roles=["learner"])
    login(subject="learner-studio-gate")
    assert client.get(f"/api/v1/studio/captions/{gen['id']}").status_code == 403
    assert client.get(video_path).status_code == 200


def test_published_video_lesson_links_public_web_origin(client, make_user, login, db_session):
    make_user("admin-studio-link", roles=["learning_admin"])
    login(subject="admin-studio-link")

    gen = client.post("/api/v1/studio/generate", json={"topic": "Link Check"}).json()
    assert gen["generated_video_asset_url"], "video must render for this check"
    filename = gen["generated_video_asset_url"].rsplit("/", 1)[-1]

    pub = client.post(f"/api/v1/studio/jobs/{gen['id']}/publish", json={})
    assert pub.status_code == 200, pub.text

    from app.core.config import get_settings
    from app.modules.courses.models import Lesson, Module

    course_id = uuid.UUID(pub.json()["course_id"])
    lessons = (
        db_session.execute(
            select(Lesson)
            .join(Module, Lesson.module_id == Module.id)
            .where(Module.course_id == course_id, Lesson.content_type == "video_url")
        )
        .scalars()
        .all()
    )
    targets = [les.content for les in lessons if les.content and filename in les.content]
    expected_origin = get_settings().public_web_url.rstrip("/")
    assert targets == [f"{expected_origin}/api/studio/video-asset/{filename}"]
    assert "localhost:8000" not in targets[0]
