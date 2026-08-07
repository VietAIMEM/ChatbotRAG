"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

U = sa.Uuid()


def upgrade() -> None:
    op.create_table(
        "admins",
        sa.Column("id", U, primary_key=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_admins_username", "admins", ["username"], unique=True)
    op.create_index("ix_admins_email", "admins", ["email"], unique=True)

    op.create_table(
        "documents",
        sa.Column("id", U, primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("stored_name", sa.String(255), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("version", sa.String(64), nullable=True),
        sa.Column("document_type", sa.String(16), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("file_path", sa.String(1024), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'UPLOADING'")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("department", sa.String(128), nullable=True),
        sa.Column("program", sa.String(128), nullable=True),
        sa.Column("language", sa.String(32), nullable=True, server_default=sa.text("'vi'")),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_documents_stored_name", "documents", ["stored_name"], unique=True)
    op.create_index("ix_documents_category", "documents", ["category"])
    op.create_index("ix_documents_year", "documents", ["year"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_is_active", "documents", ["is_active"])

    op.create_table(
        "document_chunks",
        sa.Column("id", U, primary_key=True),
        sa.Column("document_id", U, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(255), nullable=True),
        sa.Column("point_id", sa.String(64), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("meta", sa.JSON(), nullable=True),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    op.create_index("ix_document_chunks_point_id", "document_chunks", ["point_id"])
    op.create_index(
        "ix_document_chunks_document_idx",
        "document_chunks",
        ["document_id", "chunk_index"],
    )

    op.create_table(
        "conversations",
        sa.Column("id", U, primary_key=True),
        sa.Column("client_id", sa.String(64), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, server_default=sa.text("'New Conversation'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_conversations_client_id", "conversations", ["client_id"])
    op.create_index("ix_conversations_session_id", "conversations", ["session_id"], unique=True)

    op.create_table(
        "messages",
        sa.Column("id", U, primary_key=True),
        sa.Column("conversation_id", U, sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"])

    op.create_table(
        "message_sources",
        sa.Column("id", U, primary_key=True),
        sa.Column("message_id", U, sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", U, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_id", sa.String(64), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("filename", sa.String(255), nullable=False, server_default=sa.text("''")),
        sa.Column("title", sa.String(512), nullable=False, server_default=sa.text("''")),
    )
    op.create_index("ix_message_sources_message_id", "message_sources", ["message_id"])
    op.create_index("ix_message_sources_document_id", "message_sources", ["document_id"])

    op.create_table(
        "llm_providers",
        sa.Column("id", U, primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("provider_type", sa.String(32), nullable=False, server_default=sa.text("'openai_compatible'")),
        sa.Column("base_url", sa.String(512), nullable=False, server_default=sa.text("''")),
        sa.Column("api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("model", sa.String(255), nullable=False, server_default=sa.text("''")),
        sa.Column("temperature", sa.Float(), nullable=False, server_default=sa.text("0.2")),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default=sa.text("1024")),
        sa.Column("timeout", sa.Integer(), nullable=False, server_default=sa.text("120")),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("extra", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "rag_configs",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "settings",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "system_logs",
        sa.Column("id", U, primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("level", sa.String(16), nullable=False, server_default=sa.text("'INFO'")),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("conversation_id", sa.String(64), nullable=True),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("rewritten_query", sa.Text(), nullable=True),
        sa.Column("retrieved_documents", sa.JSON(), nullable=True),
        sa.Column("retrieved_scores", sa.JSON(), nullable=True),
        sa.Column("reranker_scores", sa.JSON(), nullable=True),
        sa.Column("selected_sources", sa.JSON(), nullable=True),
        sa.Column("llm_provider", sa.String(128), nullable=True),
        sa.Column("llm_model", sa.String(255), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default=sa.text("'ok'")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
    )
    op.create_index("ix_system_logs_timestamp", "system_logs", ["timestamp"])
    op.create_index("ix_system_logs_level", "system_logs", ["level"])
    op.create_index("ix_system_logs_event_type", "system_logs", ["event_type"])
    op.create_index("ix_system_logs_conversation_id", "system_logs", ["conversation_id"])


def downgrade() -> None:
    op.drop_table("system_logs")
    op.drop_table("settings")
    op.drop_table("rag_configs")
    op.drop_table("llm_providers")
    op.drop_table("message_sources")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("admins")
