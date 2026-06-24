"""merge migration heads

Revision ID: f6b7164d8634
Revises: 5785b056c910, a1b2c3d4e5f6
Create Date: 2026-06-24 14:57:11.474223
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6b7164d8634'
down_revision: Union[str, None] = ('5785b056c910', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
