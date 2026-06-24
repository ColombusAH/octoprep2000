"""add slide_events table

Revision ID: f3a8c1d902ef
Revises: d7e1f4a902bc
Create Date: 2026-06-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f3a8c1d902ef"
down_revision: Union[str, None] = "d7e1f4a902bc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "slide_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("slide_index", sa.Integer(), nullable=False),
        sa.Column("timestamp_ms", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=16), server_default="manual", nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.session_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_slide_events_session_id_timestamp_ms",
        "slide_events",
        ["session_id", "timestamp_ms"],
    )


def downgrade() -> None:
    op.drop_index("ix_slide_events_session_id_timestamp_ms", table_name="slide_events")
    op.drop_table("slide_events")
