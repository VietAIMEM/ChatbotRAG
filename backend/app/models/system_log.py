from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemLog(Base):
    __tablename__ = "system_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    level: Mapped[str] = mapped_column(String(16), default="INFO", index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    conversation_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    rewritten_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    retrieved_documents: Mapped[Any] = mapped_column(JSON, nullable=True)
    retrieved_scores: Mapped[Any] = mapped_column(JSON, nullable=True)
    reranker_scores: Mapped[Any] = mapped_column(JSON, nullable=True)
    selected_sources: Mapped[Any] = mapped_column(JSON, nullable=True)
    llm_provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="ok")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    details: Mapped[Any] = mapped_column(JSON, nullable=True)
