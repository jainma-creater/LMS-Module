"""Request and response schemas for AI Training Studio."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.courses.models import DifficultyLevel, LessonContentType


class StoryboardScene(BaseModel):
    scene_number: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=200)
    narration: str = Field(min_length=1, max_length=5000)
    visual_prompt: str = Field(min_length=1, max_length=1000)
    duration_sec: int = Field(ge=1, le=600)


class LessonDraft(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    content_type: LessonContentType = LessonContentType.TEXT
    content: str | None = Field(default=None, max_length=100000)
    estimated_minutes: int = Field(default=5, ge=1, le=120)
    is_required: bool = True


class ModuleDraft(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    lessons: list[LessonDraft] = Field(min_length=1)


class CourseDraft(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=20000)
    category: str = Field(default="Professional Development", max_length=100)
    difficulty_level: DifficultyLevel = DifficultyLevel.BEGINNER
    learning_objectives: list[str] = Field(default_factory=list)
    key_takeaways: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    modules: list[ModuleDraft] = Field(min_length=1)
    storyboard: list[StoryboardScene] = Field(default_factory=list)
    captions_vtt: str | None = None
    is_mandatory: bool = False
    validity_days: int | None = None


class QuestionOption(BaseModel):
    id: str = Field(min_length=1, max_length=10)
    text: str = Field(min_length=1, max_length=500)


class QuizQuestionDraft(BaseModel):
    question_type: str = Field(default="single_choice")
    prompt: str = Field(min_length=3, max_length=2000)
    options: list[QuestionOption] = Field(min_length=2)
    answer_key: list[str] = Field(min_length=1)
    explanation: str = Field(min_length=3, max_length=2000)
    difficulty: str = Field(default="medium")


class QuizDraft(BaseModel):
    pass_score: int = Field(default=70, ge=0, le=100)
    attempt_limit: int | None = Field(default=3, ge=1, le=10)
    questions: list[QuizQuestionDraft] = Field(min_length=1)
    # "ai" when every question came from a validated Gemini response; "template" otherwise.
    generated_by: str = Field(default="template", pattern="^(ai|template)$")


class GenerationRequest(BaseModel):
    topic: str | None = Field(default=None, max_length=2000)
    source_file_name: str | None = Field(default=None, max_length=255)
    source_text: str | None = Field(default=None, max_length=150000)
    language: str = Field(default="en", max_length=10)
    target_duration_minutes: int = Field(default=10, ge=1, le=180)
    audience: str = Field(default="all", max_length=100)
    include_quiz: bool = True
    include_video: bool = True


class GenerationJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    topic: str | None
    source_file_name: str | None
    language: str
    target_duration_minutes: int
    audience: str
    include_quiz: bool
    include_video: bool
    status: str
    progress_percent: int
    stage: str
    error_message: str | None
    retry_count: int
    generated_course_data: CourseDraft | None = None
    generated_quiz_data: QuizDraft | None = None
    generated_video_asset_url: str | None = None
    generated_video_duration_seconds: int | None = None
    published_course_id: uuid.UUID | None = None
    published_quiz_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class DraftUpdateRequest(BaseModel):
    course: CourseDraft | None = None
    quiz: QuizDraft | None = None


class RegenerateQuestionRequest(BaseModel):
    question_index: int = Field(ge=0)
    topic_hint: str | None = Field(default=None, max_length=500)


class PublishDraftRequest(BaseModel):
    assign_to_group_id: uuid.UUID | None = None
    assign_to_learner_id: uuid.UUID | None = None
    due_days: int | None = Field(default=14, ge=1, le=365)


class PublishDraftResponse(BaseModel):
    course_id: uuid.UUID
    course_slug: str
    quiz_id: uuid.UUID | None = None
    assignment_id: uuid.UUID | None = None
    group_assignment_id: uuid.UUID | None = None
    message: str
