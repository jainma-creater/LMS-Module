"""reconcile schema drift: enrollments.withdrawn_at, unused assignment exemptions

Revision ID: 0008_reconcile_schema_drift
Revises: 0007_query_indexes
Create Date: 2026-10-19

Reconciles the database with the SQLAlchemy models.

- ``enrollments.withdrawn_at`` is written by the enrollment service when an
  assignment is withdrawn, but no prior migration created the column, so the
  first withdraw/read of a learner's enrollments raised ``UndefinedColumn``.
- ``course_assignments.exempted_at/exempt_reason/exempted_by`` were added by
  0005 but are absent from the current model; no code reads or writes them. They
  are dropped so autogenerate stays clean.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008_reconcile_schema_drift"
down_revision: str | None = "0007_query_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "enrollments",
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        if_not_exists=True,
    )
    op.drop_constraint(
        "course_assignments_exempted_by_fkey",
        "course_assignments",
        type_="foreignkey",
        if_exists=True,
    )
    op.drop_column("course_assignments", "exempted_at", if_exists=True)
    op.drop_column("course_assignments", "exempted_by", if_exists=True)
    op.drop_column("course_assignments", "exempt_reason", if_exists=True)


def downgrade() -> None:
    op.add_column(
        "course_assignments",
        sa.Column("exempt_reason", sa.String(length=255), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        "course_assignments",
        sa.Column("exempted_by", sa.Uuid(), nullable=True),
        if_not_exists=True,
    )
    op.add_column(
        "course_assignments",
        sa.Column("exempted_at", sa.DateTime(timezone=True), nullable=True),
        if_not_exists=True,
    )
    op.create_foreign_key(
        "course_assignments_exempted_by_fkey",
        "course_assignments",
        "users",
        ["exempted_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_column("enrollments", "withdrawn_at", if_exists=True)
