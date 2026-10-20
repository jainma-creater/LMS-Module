"""core lms: courses, modules, lessons, enrollments, progress, assessments

Revision ID: 0003_core_lms
Revises: 0002_auth_foundation
Create Date: 2026-10-19

Adds the learning-domain tables: the course catalog (courses, modules, lessons),
enrollment/assignment, learner progress and course completion, and assessments
(quizzes, questions, attempts, responses).

Key integrity rules:
- one active (not completed) enrollment per learner/course (partial unique index)
- one progress row and one completion row per learner/lesson and learner/course
- one attempt number and one response per question per attempt
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_core_lms"
down_revision: str | None = "0002_auth_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("difficulty_level", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("slug", name="uq_courses_slug"),
    )
    op.create_index("ix_courses_status", "courses", ["status"])
    op.create_index("ix_courses_category", "courses", ["category"])
    op.create_index("ix_courses_owner_id", "courses", ["owner_id"])

    op.create_table(
        "modules",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_modules_course_id", "modules", ["course_id"])
    op.create_index("ix_modules_course_order", "modules", ["course_id", "sort_order"])

    op.create_table(
        "lessons",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("module_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=20), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default=sa.true()),
        *_timestamps(),
        sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_lessons_module_id", "lessons", ["module_id"])
    op.create_index("ix_lessons_module_order", "lessons", ["module_id", "sort_order"])

    op.create_table(
        "enrollments",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("learner_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("assignment_source", sa.String(length=20), nullable=False),
        sa.Column("assigned_by", sa.Uuid(), nullable=True),
        sa.Column(
            "assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["learner_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_enrollments_learner_id", "enrollments", ["learner_id"])
    op.create_index("ix_enrollments_course_id", "enrollments", ["course_id"])
    op.create_index("ix_enrollments_learner_status", "enrollments", ["learner_id", "status"])
    op.create_index("ix_enrollments_due_at", "enrollments", ["due_at"])
    op.create_index(
        "uq_enrollments_active",
        "enrollments",
        ["learner_id", "course_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'completed'"),
        sqlite_where=sa.text("status <> 'completed'"),
    )

    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lesson_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("last_position", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_lesson_progress_user_lesson"),
    )
    op.create_index("ix_lesson_progress_user_id", "lesson_progress", ["user_id"])
    op.create_index("ix_lesson_progress_lesson_id", "lesson_progress", ["lesson_id"])

    op.create_table(
        "course_completions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completion_rule_version", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "course_id", name="uq_course_completion_user_course"),
    )
    op.create_index("ix_course_completions_user_id", "course_completions", ["user_id"])
    op.create_index("ix_course_completions_course_id", "course_completions", ["course_id"])

    op.create_table(
        "quizzes",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=True),
        sa.Column("lesson_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("pass_score", sa.Integer(), nullable=False),
        sa.Column("attempt_limit", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "course_id IS NOT NULL OR lesson_id IS NOT NULL", name="ck_quizzes_scope"
        ),
    )
    op.create_index("ix_quizzes_course", "quizzes", ["course_id"])
    op.create_index("ix_quizzes_lesson", "quizzes", ["lesson_id"])

    op.create_table(
        "questions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("quiz_id", sa.Uuid(), nullable=False),
        sa.Column("question_type", sa.String(length=30), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options_json", sa.JSON(), nullable=False),
        sa.Column("answer_key", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("points", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_questions_quiz_id", "questions", ["quiz_id"])
    op.create_index("ix_questions_quiz_order", "questions", ["quiz_id", "sort_order"])

    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("quiz_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["quiz_id"], ["quizzes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("quiz_id", "user_id", "attempt_number", name="uq_quiz_attempt_number"),
    )
    op.create_index("ix_quiz_attempts_quiz_id", "quiz_attempts", ["quiz_id"])
    op.create_index("ix_quiz_attempts_user_id", "quiz_attempts", ["user_id"])
    op.create_index("ix_quiz_attempts_user_quiz", "quiz_attempts", ["user_id", "quiz_id"])

    op.create_table(
        "quiz_responses",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("question_id", sa.Uuid(), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("points_awarded", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["attempt_id"], ["quiz_attempts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("attempt_id", "question_id", name="uq_quiz_response_attempt_question"),
    )
    op.create_index("ix_quiz_responses_attempt_id", "quiz_responses", ["attempt_id"])
    op.create_index("ix_quiz_responses_question_id", "quiz_responses", ["question_id"])


def downgrade() -> None:
    op.drop_index("ix_quiz_responses_question_id", table_name="quiz_responses")
    op.drop_index("ix_quiz_responses_attempt_id", table_name="quiz_responses")
    op.drop_table("quiz_responses")

    op.drop_index("ix_quiz_attempts_user_quiz", table_name="quiz_attempts")
    op.drop_index("ix_quiz_attempts_user_id", table_name="quiz_attempts")
    op.drop_index("ix_quiz_attempts_quiz_id", table_name="quiz_attempts")
    op.drop_table("quiz_attempts")

    op.drop_index("ix_questions_quiz_order", table_name="questions")
    op.drop_index("ix_questions_quiz_id", table_name="questions")
    op.drop_table("questions")

    op.drop_index("ix_quizzes_lesson", table_name="quizzes")
    op.drop_index("ix_quizzes_course", table_name="quizzes")
    op.drop_table("quizzes")

    op.drop_index("ix_course_completions_course_id", table_name="course_completions")
    op.drop_index("ix_course_completions_user_id", table_name="course_completions")
    op.drop_table("course_completions")

    op.drop_index("ix_lesson_progress_lesson_id", table_name="lesson_progress")
    op.drop_index("ix_lesson_progress_user_id", table_name="lesson_progress")
    op.drop_table("lesson_progress")

    op.drop_index("uq_enrollments_active", table_name="enrollments")
    op.drop_index("ix_enrollments_due_at", table_name="enrollments")
    op.drop_index("ix_enrollments_learner_status", table_name="enrollments")
    op.drop_index("ix_enrollments_course_id", table_name="enrollments")
    op.drop_index("ix_enrollments_learner_id", table_name="enrollments")
    op.drop_table("enrollments")

    op.drop_index("ix_lessons_module_order", table_name="lessons")
    op.drop_index("ix_lessons_module_id", table_name="lessons")
    op.drop_table("lessons")

    op.drop_index("ix_modules_course_order", table_name="modules")
    op.drop_index("ix_modules_course_id", table_name="modules")
    op.drop_table("modules")

    op.drop_index("ix_courses_owner_id", table_name="courses")
    op.drop_index("ix_courses_category", table_name="courses")
    op.drop_index("ix_courses_status", table_name="courses")
    op.drop_table("courses")
