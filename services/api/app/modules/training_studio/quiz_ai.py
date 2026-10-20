"""AI quiz and assessment generation for AI Training Studio.

Questions are grounded in the approved course outline (objectives, lessons,
takeaways). Gemini returns JSON constrained by a response schema, and every
question is re-validated here before use: exactly one correct option, unique
option ids, option count bounds, and non-empty explanations. Invalid items are
dropped; if too few survive, the caller falls back to template questions and
the draft is marked ``generated_by="template"``.

Answer keys stay in the author draft and the quiz row. Learner-facing
endpoints must not return them (covered by the assessment tests).
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.config import get_settings
from app.modules.training_studio import llm_client
from app.modules.training_studio.schemas import (
    CourseDraft,
    QuestionOption,
    QuizDraft,
    QuizQuestionDraft,
)

logger = logging.getLogger(__name__)

DIFFICULTIES = ("easy", "medium", "hard")
OPTION_IDS = ("a", "b", "c", "d")
MIN_OPTIONS = 3
MAX_OPTIONS = 4
MIN_VALID_QUESTIONS = 3

_QUESTION_ITEM = {
    "type": "OBJECT",
    "properties": {
        "prompt": {"type": "STRING"},
        "difficulty": {"type": "STRING", "enum": list(DIFFICULTIES)},
        "options": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {"id": {"type": "STRING"}, "text": {"type": "STRING"}},
                "required": ["id", "text"],
            },
        },
        "correct_option_id": {"type": "STRING"},
        "explanation": {"type": "STRING"},
    },
    "required": ["prompt", "difficulty", "options", "correct_option_id", "explanation"],
}

QUIZ_SCHEMA = {
    "type": "OBJECT",
    "properties": {"questions": {"type": "ARRAY", "items": _QUESTION_ITEM}},
    "required": ["questions"],
}

QUESTION_SCHEMA = _QUESTION_ITEM

SYSTEM_INSTRUCTION = (
    "You write objective assessment questions for workplace training. Each question "
    "must test an objective or lesson from the outline, have exactly one correct "
    "option, and plausible distractors. Do not reveal the answer in the prompt. "
    "Explanations state why the correct option is right. Keep the language clear."
)


def _outline_text(course: CourseDraft) -> str:
    lines = [
        f"Course: {course.title}",
        f"Audience category: {course.category}",
        "Learning objectives:",
        *[f"- {o}" for o in course.learning_objectives],
        "Lessons:",
    ]
    for module in course.modules:
        lines.append(f"Module: {module.title}")
        lines.extend(f"- {lesson.title}: {lesson.description}" for lesson in module.lessons)
    if course.key_takeaways:
        lines.append("Key takeaways:")
        lines.extend(f"- {k}" for k in course.key_takeaways)
    return "\n".join(lines)[:6000]


def _ai_enabled() -> bool:
    return bool((get_settings().gemini_api_key or "").strip())


def _question_count(target_minutes: int) -> int:
    return max(4, min(10, round(target_minutes / 2)))


def _validate_question(raw: Any) -> QuizQuestionDraft | None:
    if not isinstance(raw, dict):
        return None
    prompt = str(raw.get("prompt", "")).strip()
    explanation = str(raw.get("explanation", "")).strip()
    difficulty = str(raw.get("difficulty", "medium")).strip().lower()
    correct = str(raw.get("correct_option_id", "")).strip().lower()
    raw_options = raw.get("options")
    if not (3 <= len(prompt) <= 2000) or len(explanation) < 3 or len(explanation) > 2000:
        return None
    if difficulty not in DIFFICULTIES or not isinstance(raw_options, list):
        return None
    if not (MIN_OPTIONS <= len(raw_options) <= MAX_OPTIONS):
        return None

    options: list[QuestionOption] = []
    seen_ids: set[str] = set()
    for item in raw_options:
        if not isinstance(item, dict):
            return None
        opt_id = str(item.get("id", "")).strip().lower()
        text = str(item.get("text", "")).strip()
        if opt_id not in OPTION_IDS or opt_id in seen_ids or not (1 <= len(text) <= 500):
            return None
        seen_ids.add(opt_id)
        options.append(QuestionOption(id=opt_id, text=text))

    if correct not in seen_ids:
        return None
    # Options must be distinct so the correct one is unambiguous.
    if len({o.text.lower() for o in options}) != len(options):
        return None

    return QuizQuestionDraft(
        question_type="single_choice",
        prompt=prompt,
        options=options,
        answer_key=[correct],
        explanation=explanation,
        difficulty=difficulty,
    )


def generate_quiz_ai(course: CourseDraft, target_minutes: int = 10) -> QuizDraft | None:
    """Return an AI-generated quiz, or None when AI is unavailable or output is unusable."""
    if not _ai_enabled():
        return None
    count = _question_count(target_minutes)
    prompt = (
        f"Write {count} single-choice questions for this outline. Mix difficulties "
        "(about one third easy, one third medium, the rest hard). Use option ids a-d. "
        "Put the correct option id in correct_option_id.\n\n"
        f"{_outline_text(course)}"
    )
    data = llm_client.generate_gemini_json(
        prompt=prompt,
        system_instruction=SYSTEM_INSTRUCTION,
        response_schema=QUIZ_SCHEMA,
    )
    if not data or not isinstance(data.get("questions"), list):
        return None

    questions = [q for q in (_validate_question(r) for r in data["questions"]) if q is not None]
    dropped = len(data["questions"]) - len(questions)
    if dropped:
        logger.info("quiz_ai dropped %s invalid question(s)", dropped)
    if len(questions) < MIN_VALID_QUESTIONS:
        return None
    return QuizDraft(
        pass_score=70,
        attempt_limit=3,
        questions=questions[:count],
        generated_by="ai",
    )


def regenerate_question_ai(
    course: CourseDraft, hint: str | None, avoid_prompts: list[str]
) -> QuizQuestionDraft | None:
    """Return one AI-written question that differs from the existing ones, or None."""
    if not _ai_enabled():
        return None
    focus = f"Focus on: {hint.strip()}\n" if hint and hint.strip() else ""
    avoid = "\n".join(f"- {p}" for p in avoid_prompts[:10])
    prompt = (
        f"{focus}Write 1 new single-choice question for this outline. Use option ids a-d and "
        "put the correct option id in correct_option_id. It must not repeat these prompts:\n"
        f"{avoid}\n\n{_outline_text(course)}"
    )
    data = llm_client.generate_gemini_json(
        prompt=prompt,
        system_instruction=SYSTEM_INSTRUCTION,
        response_schema=QUESTION_SCHEMA,
    )
    if not data:
        return None
    question = _validate_question(data)
    if question is None:
        return None
    if re.sub(r"\s+", " ", question.prompt.lower()) in {
        re.sub(r"\s+", " ", p.lower()) for p in avoid_prompts
    }:
        return None
    return question
