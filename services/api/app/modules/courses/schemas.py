"""Request/response schemas for the course catalog.

Validation lives here (and is reused by the service) so that field length,
URL scheme, tag, and lesson-content rules are explicit and independently
testable. Response models read from ORM objects via ``from_attributes``.
"""

import uuid
from datetime import datetime
from typing import Annotated
from urllib.parse import urlparse

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.modules.courses.models import CourseStatus, DifficultyLevel, LessonContentType

Tag = Annotated[str, Field(min_length=1, max_length=50)]

_HTTP_SCHEMES = frozenset({"http", "https"})


def _is_http_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme.lower() in _HTTP_SCHEMES and bool(parsed.netloc)


def _normalise_optional_url(value: str | None) -> str | None:
    """Return a validated http(s) URL, ``None`` for blank, else raise."""
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if not _is_http_url(cleaned):
        raise ValueError("must be an http(s) URL")
    return cleaned


def _normalise_tags(values: list[str]) -> list[str]:
    """Lower-case, trim, and de-duplicate tags while preserving order."""
    result: list[str] = []
    for value in values:
        cleaned = value.strip().lower()
        if cleaned and cleaned not in result:
            result.append(cleaned)
    return result


def validate_lesson_content(
    content_type: LessonContentType | str, content: str | None
) -> str | None:
    """Enforce lesson content rules for the given content type.

    ``text`` lessons hold arbitrary prose; ``video_url`` and ``external_link``
    lessons must carry a well-formed http(s) URL.
    """
    resolved = content_type.value if isinstance(content_type, LessonContentType) else content_type
    if resolved == LessonContentType.TEXT.value:
        return content.strip() if content is not None else None
    if content is None or not content.strip():
        raise ValueError("content is required and must be an http(s) URL for link/video lessons")
    cleaned = content.strip()
    if not _is_http_url(cleaned):
        raise ValueError("content must be an http(s) URL for link/video lessons")
    return cleaned


class CourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=20000)
    category: str | None = Field(default=None, max_length=100)
    difficulty_level: DifficultyLevel = DifficultyLevel.BEGINNER
    estimated_minutes: int | None = Field(default=None, ge=0, le=60000)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    tags: list[Tag] = Field(default_factory=list, max_length=20)
    is_mandatory: bool = False
    validity_days: int | None = Field(default=None, ge=1, le=3650)

    @field_validator("thumbnail_url")
    @classmethod
    def _check_thumbnail(cls, value: str | None) -> str | None:
        return _normalise_optional_url(value)

    @field_validator("tags")
    @classmethod
    def _check_tags(cls, value: list[str]) -> list[str]:
        return _normalise_tags(value)


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    short_description: str | None = Field(default=None, max_length=500)
    description: str | None = Field(default=None, max_length=20000)
    category: str | None = Field(default=None, max_length=100)
    difficulty_level: DifficultyLevel | None = None
    estimated_minutes: int | None = Field(default=None, ge=0, le=60000)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    tags: list[Tag] | None = Field(default=None, max_length=20)
    is_mandatory: bool | None = None
    validity_days: int | None = Field(default=None, ge=1, le=3650)

    @field_validator("thumbnail_url")
    @classmethod
    def _check_thumbnail(cls, value: str | None) -> str | None:
        return _normalise_optional_url(value)

    @field_validator("tags")
    @classmethod
    def _check_tags(cls, value: list[str] | None) -> list[str] | None:
        return None if value is None else _normalise_tags(value)


class CourseCounts(BaseModel):
    modules: int
    lessons: int


class CourseStatusView(BaseModel):
    """Published course as shown in the public catalog."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    short_description: str | None
    description: str | None
    category: str | None
    difficulty_level: str
    estimated_minutes: int | None
    thumbnail_url: str | None
    tags: list[str]
    version: int
    is_mandatory: bool = False
    validity_days: int | None = None


class CoursePage(BaseModel):
    """A page of published courses plus the total count for the same filters."""

    items: list[CourseStatusView]
    total: int
    limit: int
    offset: int


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    slug: str
    short_description: str | None
    description: str | None
    category: str | None
    difficulty_level: str
    estimated_minutes: int | None
    thumbnail_url: str | None
    tags: list[str]
    status: str
    owner_id: uuid.UUID | None
    version: int
    published_at: datetime | None
    is_mandatory: bool = False
    validity_days: int | None = None


class CourseDetailResponse(CourseResponse):
    model_config = ConfigDict(from_attributes=True)

    counts: CourseCounts


class LessonCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20000)
    content_type: LessonContentType = LessonContentType.TEXT
    content: str | None = Field(default=None, max_length=100000)
    estimated_minutes: int | None = Field(default=None, ge=0, le=60000)
    is_required: bool = True

    @model_validator(mode="after")
    def _check_content(self) -> "LessonCreate":
        self.content = validate_lesson_content(self.content_type, self.content)
        return self


class LessonUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20000)
    content_type: LessonContentType | None = None
    content: str | None = Field(default=None, max_length=100000)
    estimated_minutes: int | None = Field(default=None, ge=0, le=60000)
    is_required: bool | None = None


class LessonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    module_id: uuid.UUID
    title: str
    description: str | None
    content_type: str
    content: str | None
    sort_order: int
    estimated_minutes: int | None
    is_required: bool


class ModuleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20000)


class ModuleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20000)


class ModuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: str | None
    sort_order: int


class ModuleWithLessonsResponse(ModuleResponse):
    lessons: list[LessonResponse]


class CourseContentResponse(BaseModel):
    course: CourseResponse
    modules: list[ModuleWithLessonsResponse]


class ReorderRequest(BaseModel):
    ordered_ids: list[uuid.UUID] = Field(min_length=1)


__all__ = [
    "CourseContentResponse",
    "CourseCounts",
    "CourseCreate",
    "CourseDetailResponse",
    "CoursePage",
    "CourseResponse",
    "CourseStatus",
    "CourseStatusView",
    "CourseUpdate",
    "LessonCreate",
    "LessonResponse",
    "LessonUpdate",
    "ModuleCreate",
    "ModuleResponse",
    "ModuleUpdate",
    "ModuleWithLessonsResponse",
    "ReorderRequest",
    "validate_lesson_content",
]
