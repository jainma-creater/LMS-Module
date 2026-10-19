"""baseline

Revision ID: 0001_baseline
Revises:
Create Date: 2026-10-19

Empty baseline revision: establishes the alembic_version bookkeeping table.
Application tables are added by subsequent feature migrations.
"""

from collections.abc import Sequence

revision: str = "0001_baseline"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
