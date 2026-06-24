"""add analysis_phase to slide_analyses

Revision ID: d7e1f4a902bc
Revises: c4f8a2b1d903
Create Date: 2026-06-24 14:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7e1f4a902bc"
down_revision: Union[str, None] = "c4f8a2b1d903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "slide_analyses",
        sa.Column("analysis_phase", sa.String(length=16), server_default="static", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("slide_analyses", "analysis_phase")
