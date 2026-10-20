"""Persistence models for the course catalog: courses, modules, and lessons.

The course is the unit of publication; modules group lessons; lessons carry the
learning content. Ordering is explicit via ``sort_order`` and is re-assigned
atomically by the service when content is reordered.

Only role names and permissions live in code; these tables store the catalog
itself. ``owner_id`` records the author and is set to NULL if that user is later
deleted so course content is never silently removed with a user.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import AppBase


class CourseStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class DifficultyLevel(StrEnum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class LessonContentType(StrEnum):
    TEXT = "text"
    VIDEO_URL = "video_url"
    EXTERNAL_LINK = "external_link"


class Course(AppBase):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_courses_slug"),
        Index("ix_courses_status", "status"),
        Index("ix_courses_category", "category"),
        Index("ix_courses_status_created", "status", "created_at"),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    difficulty_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DifficultyLevel.BEGINNER
    )
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=CourseStatus.DRAFT)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    validity_days: Mapped[int | None] = mapped_column(Integer, nullable=True)

    tag_links: Mapped[list["CourseTag"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="CourseTag.tag",
    )

    @property
    def tags(self) -> list[str]:
        """Ordered tag names, exposed to response schemas via ``from_attributes``."""
        return [link.tag for link in self.tag_links]


class CourseTag(AppBase):
    """A single tag attached to a course (normalized for portable tag filtering)."""

    __tablename__ = "course_tags"
    __table_args__ = (
        UniqueConstraint("course_id", "tag", name="uq_course_tags_course_tag"),
        Index("ix_course_tags_tag", "tag"),
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag: Mapped[str] = mapped_column(String(50), nullable=False)

    course: Mapped[Course] = relationship(back_populates="tag_links")


class Module(AppBase):
    __tablename__ = "modules"
    __table_args__ = (Index("ix_modules_course_order", "course_id", "sort_order"),)

    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Lesson(AppBase):
    __tablename__ = "lessons"
    __table_args__ = (Index("ix_lessons_module_order", "module_id", "sort_order"),)

    module_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=LessonContentType.TEXT
    )
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
