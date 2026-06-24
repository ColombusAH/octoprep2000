"""merge slide_events and content_research

Revision ID: f663096a2c74
Revises: a1b2c3d4e5f6, f3a8c1d902ef
Create Date: 2026-06-24 13:14:22.188323
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f663096a2c74'
down_revision: Union[str, None] = ('a1b2c3d4e5f6', 'f3a8c1d902ef')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
