"""Phase 3 QA sessions, messages and citations

Revision ID: 0007_phase3_qa_engine
Revises: 0006_phase2_watch_data
Create Date: 2026-05-29

"""

from alembic import op
import sqlalchemy as sa


revision = "0007_phase3_qa_engine"
down_revision = "0006_phase2_watch_data"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # QA Sessions table
    op.create_table(
        "qa_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(256), nullable=True),
        sa.Column("status", sa.String(20), default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_qa_sessions_user_id", "qa_sessions", ["user_id"])

    # QA Messages table
    op.create_table(
        "qa_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("session_id", sa.String(36), sa.ForeignKey("qa_sessions.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("reply_to_id", sa.String(36), sa.ForeignKey("qa_messages.id"), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("status", sa.String(20), default="completed"),
        sa.Column("model_call_log_id", sa.String(36), sa.ForeignKey("model_call_logs.id"), nullable=True),
        sa.Column("error_summary", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index("ix_qa_messages_session_id", "qa_messages", ["session_id"])

    # QA Citations table
    op.create_table(
        "qa_citations",
        sa.Column("answer_message_id", sa.String(36), sa.ForeignKey("qa_messages.id"), primary_key=True),
        sa.Column("knowledge_item_id", sa.String(36), sa.ForeignKey("knowledge_items.id"), primary_key=True),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.Column("excerpt", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("qa_citations")
    op.drop_table("qa_messages")
    op.drop_table("qa_sessions")
