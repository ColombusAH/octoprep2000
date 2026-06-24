"""add speech_language/deck_language to sessions

Revision ID: 5785b056c910
Revises: c4f8a2b1d903
Create Date: 2026-06-24 13:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5785b056c910"
down_revision: Union[str, None] = "c4f8a2b1d903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("speech_language", sa.String(length=8), server_default="en", nullable=False),
    )
    op.add_column(
        "sessions",
        sa.Column("deck_language", sa.String(length=8), server_default="en", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("sessions", "deck_language")
    op.drop_column("sessions", "speech_language")
