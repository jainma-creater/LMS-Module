"""Persistence models for the AI Training Studio.

Tracks asynchronous course and video generation jobs, structured draft payloads,
and the review-and-publish workflow.
"""

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import AppBase


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    GENERATED = "generated"
    FAILED = "failed"
    PUBLISHED = "published"


class JobStage(StrEnum):
    QUEUED = "queued"
    PARSING = "parsing"
    DRAFTING_CONTENT = "drafting_content"
    DRAFTING_QUIZ = "drafting_quiz"
    RENDERING_VIDEO = "rendering_video"
    COMPLETE = "complete"
    FAILED = "failed"


class TrainingGenerationJob(AppBase):
    """Job record representing an AI course and multimedia generation task."""

    __tablename__ = "training_generation_jobs"
    __table_args__ = (
        Index("ix_training_generation_jobs_created_by", "created_by"),
        Index("ix_training_generation_jobs_status", "status"),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    target_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    audience: Mapped[str] = mapped_column(String(100), nullable=False, default="all")
    include_quiz: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    include_video: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default=JobStatus.QUEUED)
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stage: Mapped[str] = mapped_column(String(50), nullable=False, default=JobStage.QUEUED)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Generated structured payload:
    # {
    #   "title": str,
    #   "short_description": str,
    #   "description": str,
    #   "category": str,
    #   "difficulty_level": str,
    #   "learning_objectives": list[str],
    #   "key_takeaways": list[str],
    #   "tags": list[str],
    #   "modules": [
    #     {
    #       "title": str,
    #       "description": str,
    #       "lessons": [
    #         {"title": str, "content_type": str, "content": str, "estimated_minutes": int}
    #       ]
    #     }
    #   ],
    #   "storyboard": [
    #     {"scene_number": int, "title": str, "narration": str, "duration_sec": int}
    #   ],
    #   "captions_vtt": str
    # }
    generated_course_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Generated quiz payload:
    # {
    #   "pass_score": int,
    #   "attempt_limit": int,
    #   "questions": [
    #     {
    #       "question_type": str,
    #       "prompt": str,
    #       "options": [{"id": str, "text": str}],
    #       "answer_key": [str],
    #       "explanation": str,
    #       "difficulty": str
    #     }
    #   ]
    # }
    generated_quiz_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    generated_video_asset_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    generated_video_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    published_course_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    published_quiz_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("quizzes.id", ondelete="SET NULL"), nullable=True
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
