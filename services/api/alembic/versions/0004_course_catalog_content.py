"""course catalog & content: catalog metadata, tags, lesson content schema

Revision ID: 0004_course_catalog_content
Revises: 0003_core_lms
Create Date: 2026-10-19

Extends the catalog for the course-catalog milestone:

- ``courses.short_description``, ``courses.estimated_minutes`` and
  ``courses.thumbnail_url`` add catalog presentation metadata.
- ``course_tags`` normalizes course tags so tag filtering is portable and
  indexed (rather than relying on array/JSON operators).
- ``lessons.description`` adds a short summary distinct from the lesson body.
- lesson ``content_type`` values are rewritten from the earlier ``link``/``video``
  names to the explicit ``external_link`` / ``video_url`` values.

The content_type rewrite is a data migration and is reversed on downgrade.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_course_catalog_content"
down_revision: str | None = "0003_core_lms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("courses", sa.Column("short_description", sa.String(length=500), nullable=True))
    op.add_column("courses", sa.Column("estimated_minutes", sa.Integer(), nullable=True))
    op.add_column("courses", sa.Column("thumbnail_url", sa.String(length=500), nullable=True))

    op.create_table(
        "course_tags",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("tag", sa.String(length=50), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("course_id", "tag", name="uq_course_tags_course_tag"),
    )
    op.create_index("ix_course_tags_course_id", "course_tags", ["course_id"])
    op.create_index("ix_course_tags_tag", "course_tags", ["tag"])

    op.add_column("lessons", sa.Column("description", sa.Text(), nullable=True))

    op.execute("UPDATE lessons SET content_type = 'external_link' WHERE content_type = 'link'")
    op.execute("UPDATE lessons SET content_type = 'video_url' WHERE content_type = 'video'")


def downgrade() -> None:
    op.execute("UPDATE lessons SET content_type = 'link' WHERE content_type = 'external_link'")
    op.execute("UPDATE lessons SET content_type = 'video' WHERE content_type = 'video_url'")

    op.drop_column("lessons", "description")

    op.drop_index("ix_course_tags_tag", table_name="course_tags")
    op.drop_index("ix_course_tags_course_id", table_name="course_tags")
    op.drop_table("course_tags")

    op.drop_column("courses", "thumbnail_url")
    op.drop_column("courses", "estimated_minutes")
    op.drop_column("courses", "short_description")
