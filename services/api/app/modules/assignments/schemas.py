"""Request/response schemas for course assignments and group course assignments."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.enrollments.schemas import EnrollmentResponse, ProgressSummary

AssignmentStatusValue = Literal["active", "cancelled"]
DerivedStatusValue = Literal[
    "awaiting_account",
    "assigned",
    "in_progress",
    "completed",
    "withdrawn",
    "cancelled",
]


class AssignmentCreate(BaseModel):
    learner_id: uuid.UUID
    due_at: datetime | None = None


class GroupAssignmentCreate(BaseModel):
    group_id: uuid.UUID
    due_at: datetime | None = None


class AssignmentDueUpdate(BaseModel):
    due_at: datetime | None = None


class AssignmentView(BaseModel):
    """One learner's assignment, with the course, learner, group, and progress state."""

    id: uuid.UUID
    course_id: uuid.UUID
    course_title: str
    learner_id: uuid.UUID
    learner_employee_id: str
    learner_name: str
    group_assignment_id: uuid.UUID | None
    group_id: uuid.UUID | None
    group_name: str | None
    source: str
    status: str
    derived_status: str
    enrollment_id: uuid.UUID | None
    due_at: datetime | None
    overdue: bool
    assigned_at: datetime
    cancelled_at: datetime | None
    cancel_reason: str | None


class AssignmentPage(BaseModel):
    items: list[AssignmentView]
    total: int
    limit: int
    offset: int


class AssignmentDetail(AssignmentView):
    enrollment: EnrollmentResponse | None = None
    progress: ProgressSummary | None = None


class GroupAssignmentView(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    course_title: str
    group_id: uuid.UUID
    group_name: str
    status: str
    due_at: datetime | None
    assigned_at: datetime
    cancelled_at: datetime | None
    cancel_reason: str | None


class GroupAssignmentPage(BaseModel):
    items: list[GroupAssignmentView]
    total: int
    limit: int
    offset: int


class GroupAssignmentResult(BaseModel):
    """Outcome of assigning a course to a group.

    ``created`` learners received the assignment. ``skipped_existing`` already had an
    active assignment to the course. ``skipped_inactive`` are inactive learner records.
    """

    group_assignment: GroupAssignmentView
    created: int = Field(ge=0)
    skipped_existing: int = Field(ge=0)
    skipped_inactive: int = Field(ge=0)


__all__ = [
    "AssignmentCreate",
    "AssignmentDetail",
    "AssignmentDueUpdate",
    "AssignmentPage",
    "AssignmentView",
    "GroupAssignmentCreate",
    "GroupAssignmentPage",
    "GroupAssignmentResult",
    "GroupAssignmentView",
]
