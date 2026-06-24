"""add suggested_fix to slide_analyses

Revision ID: c4f8a2b1d903
Revises: 9bb93c193c03
Create Date: 2026-06-24 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4f8a2b1d903"
down_revision: Union[str, None] = "9bb93c193c03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "slide_analyses",
        sa.Column("suggested_fix", sa.Text(), server_default="", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("slide_analyses", "suggested_fix")
