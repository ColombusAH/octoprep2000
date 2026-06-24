"""add research_bundle + content_research_status to sessions

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("research_bundle", postgresql.JSONB, nullable=True))
    op.add_column(
        "sessions", sa.Column("content_research_status", sa.String(length=32), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("sessions", "content_research_status")
    op.drop_column("sessions", "research_bundle")
