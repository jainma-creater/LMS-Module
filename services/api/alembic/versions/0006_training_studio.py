"""training studio: generation jobs, storyboard assets, draft publishing

Revision ID: 0006_training_studio
Revises: 0005_compliance_foundation
Create Date: 2026-10-19

Creates the training_generation_jobs table for tracking AI course generation,
video narration storyboard pipelines, and review-before-publish workflows.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_training_studio"
down_revision: str | None = "0005_learners_assignments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "training_generation_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("topic", sa.Text(), nullable=True),
        sa.Column("source_file_name", sa.String(length=255), nullable=True),
        sa.Column("source_file_path", sa.String(length=500), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=False, server_default="en"),
        sa.Column("target_duration_minutes", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("audience", sa.String(length=100), nullable=False, server_default="all"),
        sa.Column("include_quiz", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("include_video", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stage", sa.String(length=50), nullable=False, server_default="queued"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("generated_course_data", sa.JSON(), nullable=True),
        sa.Column("generated_quiz_data", sa.JSON(), nullable=True),
        sa.Column("generated_video_asset_url", sa.String(length=500), nullable=True),
        sa.Column("generated_video_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("published_course_id", sa.Uuid(), nullable=True),
        sa.Column("published_quiz_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["published_course_id"], ["courses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["published_quiz_id"], ["quizzes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_training_generation_jobs_created_by", "training_generation_jobs", ["created_by"]
    )
    op.create_index("ix_training_generation_jobs_status", "training_generation_jobs", ["status"])


def downgrade() -> None:
    op.drop_table("training_generation_jobs")
