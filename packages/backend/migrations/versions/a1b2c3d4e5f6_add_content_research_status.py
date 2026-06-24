"""add content_research_status to reports

Revision ID: a1b2c3d4e5f6
Revises: 9bb93c193c03
Create Date: 2026-06-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "9bb93c193c03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reports", sa.Column("content_research_status", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("reports", "content_research_status")
