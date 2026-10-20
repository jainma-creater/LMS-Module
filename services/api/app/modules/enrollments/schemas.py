"""Request/response schemas for enrollment and assignment."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EnrollmentCreate(BaseModel):
    learner_id: uuid.UUID
    due_at: datetime | None = None


class EnrollmentDueUpdate(BaseModel):
    due_at: datetime | None = None


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    learner_id: uuid.UUID
    course_id: uuid.UUID
    assignment_source: str
    assigned_by: uuid.UUID | None
    assigned_at: datetime
    due_at: datetime | None
    status: str
    completed_at: datetime | None
    overdue: bool = False


class CourseSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    category: str | None
    difficulty_level: str
    status: str


class ProgressSummary(BaseModel):
    required_lessons: int
    completed_lessons: int
    percent: int
    is_complete: bool


class MyLearningItem(BaseModel):
    enrollment: EnrollmentResponse
    course: CourseSummary
    progress: ProgressSummary


class CourseEnrollmentsResponse(BaseModel):
    course_id: uuid.UUID
    enrollments: list[EnrollmentResponse]


__all__ = [
    "CourseEnrollmentsResponse",
    "CourseSummary",
    "EnrollmentCreate",
    "EnrollmentDueUpdate",
    "EnrollmentResponse",
    "MyLearningItem",
    "ProgressSummary",
]
