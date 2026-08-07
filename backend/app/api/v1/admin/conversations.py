from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.conversation import Conversation, Message
from app.schemas.conversation import ConversationDetail, ConversationListResponse, ConversationOut

router = APIRouter(prefix="/conversations", tags=["admin-conversations"])


@router.get("", response_model=ConversationListResponse)
async def admin_list_conversations(
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func

    stmt = select(Conversation)
    count_stmt = select(func.count()).select_from(Conversation)
    if q:
        stmt = stmt.where(Conversation.title.ilike(f"%{q}%") | Conversation.session_id.ilike(f"%{q}%"))
        count_stmt = count_stmt.where(
            Conversation.title.ilike(f"%{q}%") | Conversation.session_id.ilike(f"%{q}%")
        )
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(Conversation.updated_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()

    items: list[ConversationOut] = []
    for conversation in rows:
        msg_count = (
            await db.execute(
                select(func.count()).select_from(Message).where(Message.conversation_id == conversation.id)
            )
        ).scalar_one()
        last = (
            await db.execute(
                select(Message.content)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        items.append(
            ConversationOut(
                id=conversation.id,
                session_id=conversation.session_id,
                client_id=conversation.client_id,
                title=conversation.title,
                message_count=int(msg_count),
                last_message=last,
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
            )
        )
    return ConversationListResponse(items=items, total=int(total))


@router.get("/{session_id}", response_model=ConversationDetail)
async def admin_get_conversation(
    session_id: str,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services import conversation_service

    detail = await conversation_service.get_conversation_detail(db, session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return detail


@router.delete("/{session_id}")
async def admin_delete_conversation(
    session_id: str,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.services import conversation_service

    deleted = await conversation_service.delete_conversation(db, session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"message": "Conversation deleted"}
