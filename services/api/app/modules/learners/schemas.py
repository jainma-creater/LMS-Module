"""Request/response schemas for learner records and learning groups.

Validation is explicit here so field rules are testable and match the frontend
validators (``apps/web/src/lib/people.ts``).
"""

import re
import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

LearnerStatusValue = Literal["active", "inactive"]
GroupStatusValue = Literal["active", "inactive"]

EMPLOYEE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GROUP_KIND_RE = re.compile(r"^[a-z][a-z0-9_-]{0,49}$")

_Text = Annotated[str, Field(min_length=1, max_length=100)]


def _clean_optional(value: str | None, max_length: int, label: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        raise ValueError(f"{label} must be {max_length} characters or fewer")
    return cleaned


def _clean_required(value: str, max_length: int, label: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{label} is required")
    if len(cleaned) > max_length:
        raise ValueError(f"{label} must be {max_length} characters or fewer")
    return cleaned


def _check_employee_id(value: str) -> str:
    cleaned = value.strip()
    if not EMPLOYEE_ID_RE.match(cleaned):
        raise ValueError(
            "employee_id must be 1-64 letters, digits, '.', '_' or '-', "
            "starting with a letter or digit"
        )
    return cleaned


def _check_email(value: str) -> str:
    cleaned = value.strip().lower()
    if len(cleaned) > 320 or not EMAIL_RE.match(cleaned):
        raise ValueError("email must be a valid address")
    return cleaned


class LearnerCreate(BaseModel):
    employee_id: str = Field(min_length=1, max_length=64)
    first_name: _Text
    last_name: _Text
    email: str = Field(min_length=3, max_length=320)
    department: str | None = Field(default=None, max_length=120)
    business_unit: str | None = Field(default=None, max_length=120)
    status: LearnerStatusValue = "active"

    @field_validator("employee_id")
    @classmethod
    def _employee_id(cls, value: str) -> str:
        return _check_employee_id(value)

    @field_validator("first_name", "last_name")
    @classmethod
    def _names(cls, value: str) -> str:
        return _clean_required(value, 100, "Name")

    @field_validator("email")
    @classmethod
    def _email(cls, value: str) -> str:
        return _check_email(value)

    @field_validator("department", "business_unit")
    @classmethod
    def _optional(cls, value: str | None, info) -> str | None:
        return _clean_optional(value, 120, info.field_name.replace("_", " ").capitalize())


class LearnerUpdate(BaseModel):
    """Partial update. Only fields present in the request are changed.

    ``user_id`` links the learner to an identity user (or unlinks with ``null``).
    """

    employee_id: str | None = Field(default=None, min_length=1, max_length=64)
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, min_length=3, max_length=320)
    department: str | None = Field(default=None, max_length=120)
    business_unit: str | None = Field(default=None, max_length=120)
    status: LearnerStatusValue | None = None
    user_id: uuid.UUID | None = None

    @field_validator("employee_id")
    @classmethod
    def _employee_id(cls, value: str | None) -> str | None:
        return None if value is None else _check_employee_id(value)

    @field_validator("first_name", "last_name")
    @classmethod
    def _names(cls, value: str | None) -> str | None:
        return None if value is None else _clean_required(value, 100, "Name")

    @field_validator("email")
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return None if value is None else _check_email(value)

    @field_validator("department", "business_unit")
    @classmethod
    def _optional(cls, value: str | None, info) -> str | None:
        return _clean_optional(value, 120, info.field_name.replace("_", " ").capitalize())


class LearnerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    employee_id: str
    first_name: str
    last_name: str
    full_name: str
    email: str
    department: str | None
    business_unit: str | None
    status: str
    user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class LearnerPage(BaseModel):
    items: list[LearnerResponse]
    total: int
    limit: int
    offset: int


class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    kind: str = Field(default="team", max_length=50)
    status: GroupStatusValue = "active"

    @field_validator("name")
    @classmethod
    def _name(cls, value: str) -> str:
        return _clean_required(value, 120, "Name")

    @field_validator("description")
    @classmethod
    def _description(cls, value: str | None) -> str | None:
        return _clean_optional(value, 2000, "Description")

    @field_validator("kind")
    @classmethod
    def _kind(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if not GROUP_KIND_RE.match(cleaned):
            raise ValueError(
                "kind must be 1-50 lower-case letters, digits, '_' or '-', starting with a letter"
            )
        return cleaned


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    kind: str | None = Field(default=None, max_length=50)
    status: GroupStatusValue | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        return None if value is None else _clean_required(value, 120, "Name")

    @field_validator("description")
    @classmethod
    def _description(cls, value: str | None) -> str | None:
        return _clean_optional(value, 2000, "Description")

    @field_validator("kind")
    @classmethod
    def _kind(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip().lower()
        if not GROUP_KIND_RE.match(cleaned):
            raise ValueError(
                "kind must be 1-50 lower-case letters, digits, '_' or '-', starting with a letter"
            )
        return cleaned


class GroupResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    kind: str
    status: str
    member_count: int
    created_at: datetime
    updated_at: datetime


class GroupPage(BaseModel):
    items: list[GroupResponse]
    total: int
    limit: int
    offset: int


class MemberAdd(BaseModel):
    learner_id: uuid.UUID


class MemberResponse(BaseModel):
    membership_id: uuid.UUID
    learner_id: uuid.UUID
    employee_id: str
    full_name: str
    email: str
    learner_status: str
    added_at: datetime
    removed_at: datetime | None


class MemberPage(BaseModel):
    items: list[MemberResponse]
    total: int
    limit: int
    offset: int


class MemberRemovedResponse(BaseModel):
    learner_id: uuid.UUID
    group_id: uuid.UUID
    assignments_cancelled: int = Field(ge=0)


__all__ = [
    "GroupCreate",
    "GroupPage",
    "GroupResponse",
    "GroupUpdate",
    "LearnerCreate",
    "LearnerPage",
    "LearnerResponse",
    "LearnerUpdate",
    "MemberAdd",
    "MemberPage",
    "MemberResponse",
]
