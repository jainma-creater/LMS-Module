"""AI course and assessment generation engine.

Generates structured course syllabi, module outlines, lesson content,
learning objectives, and validated objective quiz questions.
Grounded in supplied topic or extracted source documents.
"""

import re

from app.modules.courses.models import DifficultyLevel, LessonContentType
from app.modules.training_studio import quiz_ai
from app.modules.training_studio.llm_client import generate_structured_content
from app.modules.training_studio.schemas import (
    CourseDraft,
    LessonDraft,
    ModuleDraft,
    QuestionOption,
    QuizDraft,
    QuizQuestionDraft,
)


def generate_course_from_source(
    *,
    topic: str | None,
    source_text: str | None,
    language: str = "en",
    target_duration_minutes: int = 10,
    audience: str = "all",
) -> CourseDraft:
    """Generate structured course metadata, modules, and lessons grounded in input."""
    # Attempt AI structured generation via Gemini or GroqCloud if configured
    if topic or source_text:
        ai_prompt = (
            f"Topic: {topic or 'Corporate Training'}\n"
            f"Audience: {audience}\n"
            f"Language: {language}\n"
            f"Target Duration: {target_duration_minutes} minutes\n"
            f"Source Content Excerpt: {(source_text or '')[:2500]}\n\n"
            "Generate complete structured training with: title, short_description, description, "
            "category, difficulty_level ('beginner', 'intermediate', 'advanced'), "
            "learning_objectives (list of 3-4 strings), key_takeaways (list of 2-3 strings), "
            "tags (list of strings), and modules (2-3 modules, each with 2-3 lessons "
            "having title, description, content_type='text', content, estimated_minutes, "
            "is_required=true)."
        )
        ai_data = generate_structured_content(prompt=ai_prompt)
        has_mods = (
            ai_data and isinstance(ai_data.get("modules"), list) and len(ai_data["modules"]) > 0
        )
        if has_mods and ai_data is not None:
            try:
                ai_data.setdefault("category", "General Training")
                ai_data.setdefault("difficulty_level", DifficultyLevel.BEGINNER)
                ai_data.setdefault("storyboard", [])
                ai_data.setdefault("captions_vtt", None)
                cat_lower = ai_data.get("category", "").lower()
                ai_data.setdefault("is_mandatory", "compliance" in cat_lower)
                ai_data.setdefault("validity_days", 365 if ai_data.get("is_mandatory") else None)
                return CourseDraft.model_validate(ai_data)
            except Exception:
                pass

    # Derive title
    raw_title = topic or "Enterprise Training"
    if source_text and not topic:
        # Extract title from the first non-empty line of source text
        first_line = next((line.strip() for line in source_text.splitlines() if line.strip()), "")
        if first_line:
            raw_title = first_line[:100]

    title = _clean_title(raw_title)

    # Summarize or synthesize content
    base_context = (
        source_text or topic or "Core professional principles and best practices"
    ).strip()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", base_context) if len(s.strip()) > 10]

    short_desc = (sentences[0] if sentences else f"Essential {title} training for {audience}.")[
        :450
    ]

    objectives = [
        f"Understand the core definitions and regulatory context of {title}.",
        "Apply standard operating procedures and best practices in daily operations.",
        "Identify common compliance risks, security vulnerabilities, or operational pitfalls.",
        "Demonstrate mastery through practical scenarios and knowledge assessments.",
    ]

    key_takeaways = [
        f"{title} principles must be followed consistently across all {audience} teams.",
        "Report ambiguities or suspicious discrepancies immediately through authorized channels.",
        "Regular recertification maintains organizational compliance and standard adherence.",
    ]

    # Generate 2 to 3 modules with 2 to 3 lessons each
    modules: list[ModuleDraft] = [
        ModuleDraft(
            title=f"Module 1: Fundamentals of {title}",
            description=f"Overview, principles, and key responsibilities for {title}.",
            lessons=[
                LessonDraft(
                    title="Introduction and Scope",
                    description="Context, definitions, and policy overview.",
                    content_type=LessonContentType.TEXT,
                    content=(
                        f"### Welcome to {title}\n\n"
                        f"This training provides {audience} members with the knowledge required "
                        f"to execute their responsibilities safely, ethically, and effectively.\n\n"
                        "#### Core Principles\n\n"
                        "- **Integrity**: Always adhere to established corporate standards.\n"
                        "- **Accountability**: Know your role and document required actions.\n"
                        "- **Vigilance**: Identify and escalate deviations promptly.\n"
                    ),
                    estimated_minutes=max(2, target_duration_minutes // 4),
                    is_required=True,
                ),
                LessonDraft(
                    title="Key Concepts and Terminology",
                    description="Essential terms, definitions, and boundaries.",
                    content_type=LessonContentType.TEXT,
                    content=(
                        "### Essential Terminology\n\n"
                        "Familiarize yourself with primary terms used throughout this course:\n\n"
                        "1. **Governing Policy**: Corporate standard approved by leadership.\n"
                        "2. **Standard Operating Procedure (SOP)**: Step-by-step instructions.\n"
                        "3. **Incident Escalation**: Defined path to notify supervisors.\n"
                    ),
                    estimated_minutes=max(2, target_duration_minutes // 4),
                    is_required=True,
                ),
            ],
        ),
        ModuleDraft(
            title="Module 2: Practical Application & Procedures",
            description="Real-world workflows, scenarios, and execution guidelines.",
            lessons=[
                LessonDraft(
                    title="Standard Operating Guidelines",
                    description="Detailed process workflows and decision-making criteria.",
                    content_type=LessonContentType.TEXT,
                    content=(
                        "### Step-by-Step Procedure\n\n"
                        "Follow this workflow when handling relevant tasks:\n\n"
                        "1. **Verify Authorization**: Confirm you have the required context.\n"
                        "2. **Execute According to Policy**: Never skip verification gates.\n"
                        "3. **Record Evidence**: Retain auditable records and logs.\n"
                        "4. **Report Deviations**: Escalate immediately if an anomaly occurs.\n"
                    ),
                    estimated_minutes=max(3, target_duration_minutes // 3),
                    is_required=True,
                ),
                LessonDraft(
                    title="Scenario Analysis & Risk Prevention",
                    description="Common pitfalls, edge cases, and mitigation strategies.",
                    content_type=LessonContentType.TEXT,
                    content=(
                        "### Case Studies & Best Practices\n\n"
                        "Examine realistic workplace scenarios:\n\n"
                        "- **Scenario A**: Always pause and request clarification "
                        "rather than guessing.\n"
                        "- **Scenario B**: Compliance and safety take precedence "
                        "over operational speed.\n"
                    ),
                    estimated_minutes=max(3, target_duration_minutes // 3),
                    is_required=True,
                ),
            ],
        ),
    ]

    # Category and tags
    category = (
        "Compliance & Ethics"
        if any(
            w in title.lower() for w in ("security", "safety", "conduct", "compliance", "privacy")
        )
        else "Professional Skills"
    )
    tags = [
        "ai-studio",
        "corporate",
        audience.lower().replace(" ", "-"),
        title.lower()[:30].strip(),
    ]

    return CourseDraft(
        title=title,
        short_description=short_desc,
        description=(
            f"Comprehensive {title} training for {audience}. "
            "Covers core standards, practical guidelines, and compliance requirements."
        ),
        category=category,
        difficulty_level=DifficultyLevel.BEGINNER,
        learning_objectives=objectives,
        key_takeaways=key_takeaways,
        tags=tags,
        modules=modules,
        storyboard=[],
        captions_vtt=None,
        is_mandatory="compliance" in category.lower(),
        validity_days=365 if "compliance" in category.lower() else None,
    )


def generate_quiz_for_course(course: CourseDraft, target_minutes: int = 10) -> QuizDraft:
    """Generate objective questions: AI-grounded when available, else template fallback."""
    ai_quiz = quiz_ai.generate_quiz_ai(course, target_minutes)
    if ai_quiz is not None:
        return ai_quiz

    questions: list[QuizQuestionDraft] = [
        QuizQuestionDraft(
            question_type="single_choice",
            prompt=f"What is the primary objective of the {course.title} policy?",
            options=[
                QuestionOption(
                    id="a",
                    text="To ensure adherence to verified operating procedures and mitigate risks",
                ),
                QuestionOption(
                    id="b", text="To eliminate all forms of documentation and reporting"
                ),
                QuestionOption(
                    id="c", text="To transfer operational accountability solely to outside vendors"
                ),
                QuestionOption(
                    id="d",
                    text="To allow employees to bypass checkpoints whenever deadlines are tight",
                ),
            ],
            answer_key=["a"],
            explanation=(
                "The policy establishes verified operating procedures and compliance controls "
                "to safeguard the organization and maintain standards."
            ),
            difficulty="beginner",
        ),
        QuizQuestionDraft(
            question_type="single_choice",
            prompt="When encountering a compliance anomaly or conflict, what should you do?",
            options=[
                QuestionOption(id="a", text="Ignore it if nobody noticed"),
                QuestionOption(
                    id="b",
                    text="Pause, consult SOP, and escalate to supervisor or compliance lead",
                ),
                QuestionOption(id="c", text="Make an unverified guess to finish quickly"),
                QuestionOption(id="d", text="Disable system audit logs to prevent error alerts"),
            ],
            answer_key=["b"],
            explanation=(
                "Safety and compliance require pausing, reviewing SOPs, and escalating "
                "issues to designated authorities rather than guessing."
            ),
            difficulty="intermediate",
        ),
        QuizQuestionDraft(
            question_type="single_choice",
            prompt="How does the organization maintain compliance recertification standards?",
            options=[
                QuestionOption(
                    id="a",
                    text="Through regular training, auditable records, and periodic checks",
                ),
                QuestionOption(id="b", text="By relying solely on unmonitored self-attestations"),
                QuestionOption(
                    id="c", text="By exempting everyone automatically after their first day"
                ),
                QuestionOption(
                    id="d", text="By deleting historical training records every quarter"
                ),
            ],
            answer_key=["a"],
            explanation=(
                "Consistent compliance relies on auditable records, ongoing training, "
                "and verifiable assessment checks."
            ),
            difficulty="beginner",
        ),
    ]

    return QuizDraft(
        pass_score=70,
        attempt_limit=3,
        questions=questions,
        generated_by="template",
    )


def regenerate_single_question(
    course: CourseDraft,
    question_index: int,
    hint: str | None = None,
    avoid_prompts: list[str] | None = None,
) -> QuizQuestionDraft:
    """Generate a single refreshed question. AI first; template fallback if unavailable."""
    ai_question = quiz_ai.regenerate_question_ai(course, hint, avoid_prompts or [])
    if ai_question is not None:
        return ai_question

    topic_label = hint or course.title
    return QuizQuestionDraft(
        question_type="single_choice",
        prompt=f"Which option best reflects an approved standard regarding {topic_label}?",
        options=[
            QuestionOption(
                id="a",
                text="Following documented procedures and verifying all required checklist gates",
            ),
            QuestionOption(
                id="b", text="Proceeding without authorization when time is constrained"
            ),
            QuestionOption(
                id="c", text="Assuming informal guidelines replace formal corporate policy"
            ),
            QuestionOption(
                id="d", text="Sharing restricted training materials on public social channels"
            ),
        ],
        answer_key=["a"],
        explanation=(
            f"Approved standards for {topic_label} mandate strict adherence to "
            "documented procedures and verified checkpoints."
        ),
        difficulty="medium",
    )


def _clean_title(raw: str) -> str:
    cleaned = re.sub(r"^[0-9.\-\s]+", "", raw).strip()
    cleaned = cleaned.replace("_", " ").replace("-", " ")
    return cleaned.title()[:120] or "Enterprise Training"
