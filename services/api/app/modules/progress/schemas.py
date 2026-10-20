"""Request/response schemas for learning progress and completion."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.progress.models import LessonProgressStatus


class LessonProgressUpdate(BaseModel):
    status: LessonProgressStatus = LessonProgressStatus.IN_PROGRESS
    last_position: int | None = Field(default=None, ge=0)


class LessonProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lesson_id: uuid.UUID
    status: str
    last_position: int | None
    completed_at: datetime | None


class CourseProgressResponse(BaseModel):
    course_id: uuid.UUID
    required_lessons: int
    completed_lessons: int
    percent: int
    is_complete: bool
    lessons: list[LessonProgressResponse]


class CompletionItem(BaseModel):
    course_id: uuid.UUID
    course_title: str
    completed_at: datetime
    completion_rule_version: int
