"""Request/response schemas for assessments.

Learner-facing question schemas deliberately omit ``answer_key`` and
``explanation`` so the correct answers can never be serialized before
submission.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.assessments.models import QuestionType


class Option(BaseModel):
    id: str = Field(min_length=1, max_length=50)
    text: str = Field(min_length=1, max_length=2000)


class QuizCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20000)
    course_id: uuid.UUID | None = None
    lesson_id: uuid.UUID | None = None
    pass_score: int = Field(default=70, ge=0, le=100)
    attempt_limit: int | None = Field(default=None, ge=1, le=1000)


class QuizUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20000)
    pass_score: int | None = Field(default=None, ge=0, le=100)
    attempt_limit: int | None = Field(default=None, ge=1, le=1000)


class QuizResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID | None
    lesson_id: uuid.UUID | None
    title: str
    description: str | None
    pass_score: int
    attempt_limit: int | None
    status: str


class QuestionCreate(BaseModel):
    question_type: QuestionType = QuestionType.SINGLE_CHOICE
    prompt: str = Field(min_length=1, max_length=20000)
    options: list[Option] = Field(min_length=2)
    answer_key: list[str] = Field(min_length=1)
    explanation: str | None = Field(default=None, max_length=20000)
    points: int = Field(default=1, ge=1, le=100)


class QuestionUpdate(BaseModel):
    prompt: str | None = Field(default=None, min_length=1, max_length=20000)
    options: list[Option] | None = Field(default=None, min_length=2)
    answer_key: list[str] | None = Field(default=None, min_length=1)
    explanation: str | None = Field(default=None, max_length=20000)
    points: int | None = Field(default=None, ge=1, le=100)


class QuestionAuthorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    question_type: str
    prompt: str
    options: list[Option]
    answer_key: list[str]
    explanation: str | None
    sort_order: int
    points: int


class QuestionLearnerResponse(BaseModel):
    id: uuid.UUID
    question_type: str
    prompt: str
    options: list[Option]
    sort_order: int
    points: int


class QuizAuthorDetail(QuizResponse):
    questions: list[QuestionAuthorResponse]


class QuizLearnerDetail(QuizResponse):
    questions: list[QuestionLearnerResponse]


class AnswerSubmission(BaseModel):
    question_id: uuid.UUID
    selected: list[str] = Field(default_factory=list)


class AttemptSubmitRequest(BaseModel):
    answers: list[AnswerSubmission] = Field(default_factory=list)


class AttemptStartResponse(BaseModel):
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    attempt_number: int
    status: str
    started_at: datetime
    questions: list[QuestionLearnerResponse]


class ResponseResult(BaseModel):
    question_id: uuid.UUID
    selected: list[str]
    is_correct: bool
    points_awarded: int
    explanation: str | None


class AttemptResult(BaseModel):
    attempt_id: uuid.UUID
    quiz_id: uuid.UUID
    attempt_number: int
    status: str
    score: int | None
    passed: bool | None
    started_at: datetime
    submitted_at: datetime | None
    results: list[ResponseResult]


class AttemptSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quiz_id: uuid.UUID
    attempt_number: int
    status: str
    score: int | None
    passed: bool | None
    started_at: datetime
    submitted_at: datetime | None
