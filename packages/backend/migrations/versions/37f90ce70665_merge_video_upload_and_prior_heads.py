"""merge video upload and prior heads

Revision ID: 37f90ce70665
Revises: c3d4e5f6a7b8, f042d392bed9
Create Date: 2026-06-24 14:35:46.457863
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '37f90ce70665'
down_revision: Union[str, None] = ('c3d4e5f6a7b8', 'f042d392bed9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
