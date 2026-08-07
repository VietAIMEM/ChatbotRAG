from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class SystemLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    timestamp: datetime
    level: str
    event_type: str
    conversation_id: str | None = None
    question: str | None = None
    rewritten_query: str | None = None
    retrieved_documents: Any = None
    retrieved_scores: Any = None
    reranker_scores: Any = None
    selected_sources: Any = None
    llm_provider: str | None = None
    llm_model: str | None = None
    latency_ms: float | None = None
    status: str
    error: str | None = None
    details: Any = None


class SystemLogListResponse(BaseModel):
    items: list[SystemLogOut]
    total: int


class DashboardStats(BaseModel):
    total_documents: int
    indexed_documents: int
    processing_documents: int
    failed_documents: int
    total_conversations: int
    total_messages: int
    llm_requests: int
    rag_queries: int
    recent_activity: list[SystemLogOut] = []
