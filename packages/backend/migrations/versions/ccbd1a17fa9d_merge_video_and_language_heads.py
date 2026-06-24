"""merge video and language heads

Revision ID: ccbd1a17fa9d
Revises: 37f90ce70665, f6b7164d8634
Create Date: 2026-06-24 16:58:19.966839
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ccbd1a17fa9d'
down_revision: Union[str, None] = ('37f90ce70665', 'f6b7164d8634')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
