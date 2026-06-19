"""initial schema

Revision ID: e6dc02351acc
Revises:
Create Date: 2026-06-17 22:49:48.733847
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

# revision identifiers, used by Alembic.
revision: str = 'e6dc02351acc'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("session_id", UUID(as_uuid=True), primary_key=True),
        sa.Column("access_token", UUID(as_uuid=True), nullable=False),
        sa.Column("topic", sa.Text, nullable=False),
        sa.Column("topic_context", sa.Text, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"),
        sa.Column("pptx_ready", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("slides_raw_text", JSONB, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "transcript_entries",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("start_ms", sa.Integer, nullable=False),
        sa.Column("end_ms", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("filler_flags", ARRAY(sa.String), nullable=True),
    )

    op.create_table(
        "video_events",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("timestamp_ms", sa.Integer, nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("raw_metadata", JSONB, nullable=True),
    )

    op.create_table(
        "slide_analyses",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("slide_index", sa.Integer, nullable=False),
        sa.Column("playbook_factor", sa.Integer, nullable=False),
        sa.Column("finding_type", sa.String(16), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.session_id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("overall_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("voice_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("body_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("slide_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("content_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("insights", JSONB, nullable=True),
        sa.Column("mentor_unlocked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("share_token", UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("slide_analyses")
    op.drop_table("video_events")
    op.drop_table("transcript_entries")
    op.drop_table("sessions")
