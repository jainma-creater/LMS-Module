"""Tests for AI quiz generation and validation in AI Training Studio."""

from app.core.config import get_settings
from app.modules.assessments.schemas import QuestionLearnerResponse
from app.modules.training_studio import generator, llm_client, quiz_ai
from app.modules.training_studio.schemas import CourseDraft, LessonDraft, ModuleDraft


def _course() -> CourseDraft:
    return CourseDraft(
        title="Phishing Defense",
        short_description="Short",
        description="Long description.",
        category="Security",
        difficulty_level="beginner",
        learning_objectives=["Spot phishing", "Report it", "Stay calm"],
        key_takeaways=["Never share credentials"],
        tags=["security"],
        is_mandatory=False,
        validity_days=None,
        modules=[
            ModuleDraft(
                title="Signals",
                description="Signals",
                lessons=[
                    LessonDraft(
                        title="Urgency cues",
                        description="Urgent wording is a warning sign.",
                        content_type="text",
                        content="Text",
                        estimated_minutes=3,
                        is_required=True,
                    )
                ],
            )
        ],
    )


def _good(i: int, difficulty: str = "easy") -> dict:
    return {
        "prompt": f"Question number {i}: what should you do with a suspicious link?",
        "difficulty": difficulty,
        "options": [
            {"id": "a", "text": "Click it to check"},
            {"id": "b", "text": "Report it using the report button"},
            {"id": "c", "text": "Forward it to coworkers"},
        ],
        "correct_option_id": "b",
        "explanation": "Reporting lets the security team block the sender.",
    }


def _enable_key(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", "test-key")


def test_ai_quiz_uses_validated_questions_and_marks_source(monkeypatch):
    _enable_key(monkeypatch)
    monkeypatch.setattr(
        llm_client,
        "generate_gemini_json",
        lambda **_kw: {"questions": [_good(i, "hard") for i in range(4)]},
    )
    quiz = quiz_ai.generate_quiz_ai(_course(), target_minutes=10)
    assert quiz is not None
    assert quiz.generated_by == "ai"
    assert len(quiz.questions) == 4
    for q in quiz.questions:
        assert q.answer_key == ["b"]
        assert {o.id for o in q.options} >= set(q.answer_key)


def test_invalid_ai_questions_are_dropped(monkeypatch):
    _enable_key(monkeypatch)
    bad_no_correct = {**_good(90), "correct_option_id": "z"}
    bad_duplicate_text = {
        **_good(91),
        "options": [
            {"id": "a", "text": "Same"},
            {"id": "b", "text": "same"},
            {"id": "c", "text": "Other"},
        ],
        "correct_option_id": "a",
    }
    bad_difficulty = {**_good(92), "difficulty": "impossible"}
    valid = [_good(i) for i in range(3)]
    monkeypatch.setattr(
        llm_client,
        "generate_gemini_json",
        lambda **_kw: {"questions": [bad_no_correct, bad_duplicate_text, bad_difficulty, *valid]},
    )
    quiz = quiz_ai.generate_quiz_ai(_course(), target_minutes=6)
    assert quiz is not None
    assert len(quiz.questions) == 3


def test_too_few_valid_ai_questions_falls_back_to_template(monkeypatch):
    _enable_key(monkeypatch)
    monkeypatch.setattr(
        llm_client,
        "generate_gemini_json",
        lambda **_kw: {"questions": [{"prompt": "x"}]},
    )
    assert quiz_ai.generate_quiz_ai(_course()) is None
    quiz = generator.generate_quiz_for_course(_course())
    assert quiz.generated_by == "template"
    assert len(quiz.questions) == 3


def test_no_key_means_template_quiz_without_network(monkeypatch):
    monkeypatch.setattr(get_settings(), "gemini_api_key", None)

    def must_not_call(**_kw):
        raise AssertionError("LLM must not be called without a key")

    monkeypatch.setattr(llm_client, "generate_gemini_json", must_not_call)
    quiz = generator.generate_quiz_for_course(_course())
    assert quiz.generated_by == "template"


def test_regenerated_question_must_differ_from_existing_prompts(monkeypatch):
    _enable_key(monkeypatch)
    repeated = _good(1)
    monkeypatch.setattr(llm_client, "generate_gemini_json", lambda **_kw: repeated)
    assert quiz_ai.regenerate_question_ai(_course(), None, [repeated["prompt"]]) is None
    fresh = quiz_ai.regenerate_question_ai(_course(), "urgency", ["something else"])
    assert fresh is not None
    assert fresh.answer_key == ["b"]


def test_learner_question_schema_never_exposes_answer_key():
    assert "answer_key" not in QuestionLearnerResponse.model_fields
