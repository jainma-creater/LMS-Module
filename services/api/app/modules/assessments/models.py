"""Persistence models for assessments: quizzes, questions, attempts, responses.

Security note: ``Question.answer_key`` is the correct-answer key and must never
be serialized to learner-facing responses before submission. Learner schemas
omit it by construction (see ``schemas.py``). Scoring is computed server-side
from the stored key; a client never supplies a score or pass flag.

Attempts and responses are retained as history rather than overwritten.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppBase


class QuizStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class QuestionType(StrEnum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"


class AttemptStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"


class Quiz(AppBase):
    __tablename__ = "quizzes"
    __table_args__ = (
        CheckConstraint("course_id IS NOT NULL OR lesson_id IS NOT NULL", name="ck_quizzes_scope"),
        Index("ix_quizzes_course", "course_id"),
        Index("ix_quizzes_lesson", "lesson_id"),
    )

    course_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), nullable=True
    )
    lesson_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    pass_score: Mapped[int] = mapped_column(Integer, nullable=False, default=70)
    attempt_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=QuizStatus.DRAFT)


class Question(AppBase):
    __tablename__ = "questions"
    __table_args__ = (Index("ix_questions_quiz_order", "quiz_id", "sort_order"),)

    quiz_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default=QuestionType.SINGLE_CHOICE
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    answer_key: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class QuizAttempt(AppBase):
    __tablename__ = "quiz_attempts"
    __table_args__ = (
        UniqueConstraint("quiz_id", "user_id", "attempt_number", name="uq_quiz_attempt_number"),
        Index("ix_quiz_attempts_user_quiz", "user_id", "quiz_id"),
    )

    quiz_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AttemptStatus.IN_PROGRESS
    )
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool | None] = mapped_column(nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class QuizResponse(AppBase):
    __tablename__ = "quiz_responses"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_quiz_response_attempt_question"),
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    response_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_correct: Mapped[bool | None] = mapped_column(nullable=True)
    points_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
