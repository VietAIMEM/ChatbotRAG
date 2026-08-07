from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetail,
    ConversationListResponse,
    ConversationOut,
)
from app.services import conversation_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    client_id: str,
    db: AsyncSession = Depends(get_db),
):
    items = await conversation_service.list_conversations(db, client_id)
    return ConversationListResponse(items=items, total=len(items))


@router.post("", response_model=ConversationOut)
async def create_conversation(
    payload: ConversationCreate,
    db: AsyncSession = Depends(get_db),
):
    conversation = await conversation_service.get_or_create_conversation(
        db, payload.client_id, title=payload.title
    )
    return conversation_service._conversation_out(conversation)


@router.get("/{session_id}", response_model=ConversationDetail)
async def get_conversation(
    session_id: str,
    client_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    detail = await conversation_service.get_conversation_detail(db, session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if client_id and detail.client_id != client_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return detail


@router.delete("/{session_id}")
async def delete_conversation(
    session_id: str,
    client_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    deleted = await conversation_service.delete_conversation(db, session_id, client_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted"}
