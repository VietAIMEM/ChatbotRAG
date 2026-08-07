from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.chat import SourceOut


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    sources: list[SourceOut] = []


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: str
    client_id: str
    title: str
    message_count: int = 0
    last_message: str | None = None
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    id: uuid.UUID
    session_id: str
    client_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []


class ConversationListResponse(BaseModel):
    items: list[ConversationOut]
    total: int


class ConversationCreate(BaseModel):
    client_id: str
    title: str | None = None
