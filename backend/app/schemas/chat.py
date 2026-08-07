from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    client_id: str = Field(min_length=8, max_length=128)
    question: str = Field(min_length=1, max_length=4000)


class SourceOut(BaseModel):
    document_id: uuid.UUID
    filename: str
    title: str
    document_type: str
    page_number: int | None = None
    chunk_id: str
    relevance_score: float
    download_url: str
    view_url: str


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: uuid.UUID
    answer: str
    sources: list[SourceOut] = []
    rewritten_query: str | None = None
    grounded: bool = True


class SSEEvent(BaseModel):
    type: str  # start | delta | done | error | sources
    data: dict = {}


class DomainRejection(BaseModel):
    rejected: bool = True
    reason: str = "Sorry, I can only assist with postgraduate education information contained in the available documents."
