"""query indexes for catalog, progress and completion read paths

Revision ID: 0007_query_indexes
Revises: 0006_training_studio
Create Date: 2026-10-19

Adds composite indexes for the hot read paths used by the learner catalog,
My Learning and progress/completion endpoints. These turn several per-row
lookups into single indexed scans without changing any semantics.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007_query_indexes"
down_revision: str | None = "0006_training_studio"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Catalog listing: filter by status and order by created_at desc.
    op.create_index(
        "ix_courses_status_created",
        "courses",
        ["status", "created_at"],
        unique=False,
        if_not_exists=True,
    )
    # Batch completion counts: join lesson_progress filtered by user + status.
    op.create_index(
        "ix_lesson_progress_user_status",
        "lesson_progress",
        ["user_id", "status"],
        unique=False,
        if_not_exists=True,
    )
    # Completion history: list a learner's completions newest-first.
    op.create_index(
        "ix_course_completions_user_completed",
        "course_completions",
        ["user_id", "completed_at"],
        unique=False,
        if_not_exists=True,
    )
    # Course roster / group assignment fan-out by course and status.
    op.create_index(
        "ix_enrollments_course_status",
        "enrollments",
        ["course_id", "status"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_enrollments_course_status", table_name="enrollments", if_exists=True)
    op.drop_index(
        "ix_course_completions_user_completed",
        table_name="course_completions",
        if_exists=True,
    )
    op.drop_index("ix_lesson_progress_user_status", table_name="lesson_progress", if_exists=True)
    op.drop_index("ix_courses_status_created", table_name="courses", if_exists=True)
