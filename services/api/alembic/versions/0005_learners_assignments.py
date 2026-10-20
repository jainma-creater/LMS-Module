"""learners, groups, assignments, and compliance foundation

Revision ID: 0005_learners_assignments
Revises: 0004_course_catalog_content
Create Date: 2026-10-19

Creates learner directory, learning groups, group memberships, group course assignments,
individual course assignments, and compliance fields on courses.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_learners_assignments"
down_revision: str | None = "0004_course_catalog_content"
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
    # 1. Learners
    op.create_table(
        "learners",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("employee_id", sa.String(length=64), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("department", sa.String(length=120), nullable=True),
        sa.Column("business_unit", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("employee_id", name="uq_learners_employee_id"),
        sa.UniqueConstraint("email", name="uq_learners_email"),
        sa.UniqueConstraint("user_id", name="uq_learners_user_id"),
    )
    op.create_index("ix_learners_status", "learners", ["status"])
    op.create_index("ix_learners_department", "learners", ["department"])

    # 2. Learning groups
    op.create_table(
        "learning_groups",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("kind", sa.String(length=50), nullable=False, server_default="team"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        *_timestamps(),
        sa.UniqueConstraint("name", name="uq_learning_groups_name"),
    )
    op.create_index("ix_learning_groups_status", "learning_groups", ["status"])

    # 3. Learning group members
    op.create_table(
        "learning_group_members",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("learner_id", sa.Uuid(), nullable=False),
        sa.Column("added_by", sa.Uuid(), nullable=True),
        sa.Column("removed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("removed_by", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["group_id"], ["learning_groups.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["learner_id"], ["learners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["added_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["removed_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "uq_group_members_active",
        "learning_group_members",
        ["group_id", "learner_id"],
        unique=True,
        postgresql_where=sa.text("removed_at IS NULL"),
        sqlite_where=sa.text("removed_at IS NULL"),
    )
    op.create_index("ix_group_members_learner", "learning_group_members", ["learner_id"])

    # 4. Group course assignments
    op.create_table(
        "group_course_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("group_id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("assigned_by", sa.Uuid(), nullable=True),
        sa.Column(
            "assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.String(length=100), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["group_id"], ["learning_groups.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "uq_group_course_assignments_active",
        "group_course_assignments",
        ["group_id", "course_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )
    op.create_index("ix_group_course_assignments_course", "group_course_assignments", ["course_id"])

    # 5. Course assignments
    op.create_table(
        "course_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("learner_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("group_assignment_id", sa.Uuid(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("assigned_by", sa.Uuid(), nullable=True),
        sa.Column(
            "assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.String(length=100), nullable=True),
        sa.Column("enrollment_id", sa.Uuid(), nullable=True),
        sa.Column("exempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exempt_reason", sa.String(length=255), nullable=True),
        sa.Column("exempted_by", sa.Uuid(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["learner_id"], ["learners.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["group_assignment_id"], ["group_course_assignments.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["exempted_by"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "uq_course_assignments_active",
        "course_assignments",
        ["course_id", "learner_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )
    op.create_index("ix_course_assignments_learner", "course_assignments", ["learner_id"])
    op.create_index(
        "ix_course_assignments_group_assignment", "course_assignments", ["group_assignment_id"]
    )
    op.create_index("ix_course_assignments_status_due", "course_assignments", ["status", "due_at"])

    # 6. Compliance fields on courses
    op.add_column(
        "courses",
        sa.Column("is_mandatory", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("courses", sa.Column("validity_days", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("courses", "validity_days")
    op.drop_column("courses", "is_mandatory")
    op.drop_table("course_assignments")
    op.drop_table("group_course_assignments")
    op.drop_table("learning_group_members")
    op.drop_table("learning_groups")
    op.drop_table("learners")
