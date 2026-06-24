"""merge session_research and slide_events heads

Revision ID: f042d392bed9
Revises: b2c3d4e5f6a7, f663096a2c74
Create Date: 2026-06-24 14:34:35.018696
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f042d392bed9'
down_revision: Union[str, None] = ('b2c3d4e5f6a7', 'f663096a2c74')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
