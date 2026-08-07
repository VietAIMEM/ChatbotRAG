from __future__ import annotations

import uuid

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message, MessageSource
from app.schemas.conversation import ConversationDetail, ConversationOut, MessageOut
from app.schemas.chat import SourceOut


def _source_out(source: MessageSource) -> SourceOut:
    return SourceOut(
        document_id=source.document_id,
        filename=source.filename,
        title=source.title,
        document_type="",
        page_number=source.page_number,
        chunk_id=source.chunk_id,
        relevance_score=source.score,
        download_url=f"/api/documents/{source.document_id}/download",
        view_url=f"/api/documents/{source.document_id}/view",
    )


def _message_out(message: Message) -> MessageOut:
    return MessageOut(
        id=message.id,
        role=message.role,
        content=message.content,
        created_at=message.created_at,
        sources=[_source_out(s) for s in message.sources],
    )


def _conversation_out(conversation: Conversation, message_count: int = 0, last_message: str | None = None) -> ConversationOut:
    return ConversationOut(
        id=conversation.id,
        session_id=conversation.session_id,
        client_id=conversation.client_id,
        title=conversation.title,
        message_count=message_count,
        last_message=last_message,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


async def get_or_create_conversation(
    db: AsyncSession,
    client_id: str,
    session_id: str | None = None,
    title: str | None = None,
) -> Conversation:
    if session_id:
        result = await db.execute(
            select(Conversation).where(Conversation.session_id == session_id)
        )
        conversation = result.scalar_one_or_none()
        if conversation:
            return conversation
    conversation = Conversation(
        client_id=client_id,
        session_id=session_id or str(uuid.uuid4()),
        title=title or "New Conversation",
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def list_conversations(db: AsyncSession, client_id: str) -> list[ConversationOut]:
    result = await db.execute(
        select(
            Conversation,
            func.count(Message.id),
            func.max(Message.content),
        )
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .where(Conversation.client_id == client_id)
        .group_by(Conversation.id)
        .order_by(Conversation.updated_at.desc())
    )
    items: list[ConversationOut] = []
    for conversation, count, last_content in result.all():
        last = None
        if count:
            # max(content) is fine for a preview; full detail returns ordered messages
            result2 = await db.execute(
                select(Message.content)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.created_at.desc())
                .limit(1)
            )
            last = result2.scalar_one_or_none()
        items.append(_conversation_out(conversation, int(count or 0), last))
    return items


async def get_conversation_detail(db: AsyncSession, session_id: str) -> ConversationDetail | None:
    result = await db.execute(select(Conversation).where(Conversation.session_id == session_id))
    conversation = result.scalar_one_or_none()
    if conversation is None:
        return None
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
    )
    messages = [
        _message_out(m)
        for m in messages_result.scalars().all()
        if m.role in ("user", "assistant")
    ]
    return ConversationDetail(
        id=conversation.id,
        session_id=conversation.session_id,
        client_id=conversation.client_id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=messages,
    )


async def delete_conversation(db: AsyncSession, session_id: str, client_id: str | None = None) -> bool:
    stmt = select(Conversation).where(Conversation.session_id == session_id)
    if client_id:
        stmt = stmt.where(Conversation.client_id == client_id)
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()
    if conversation is None:
        return False
    await db.execute(sa_delete(Message).where(Message.conversation_id == conversation.id))
    await db.delete(conversation)
    await db.commit()
    return True


async def add_message(
    db: AsyncSession,
    conversation: Conversation,
    role: str,
    content: str,
    sources: list[dict] | None = None,
) -> Message:
    message = Message(conversation_id=conversation.id, role=role, content=content)
    db.add(message)
    await db.flush()
    for source in sources or []:
        source_document_id = source["document_id"]
        if isinstance(source_document_id, str):
            try:
                source_document_id = uuid.UUID(source_document_id)
            except ValueError:
                pass
        db.add(
            MessageSource(
                message_id=message.id,
                document_id=source_document_id,
                chunk_id=source["chunk_id"],
                page_number=source.get("page_number"),
                score=source.get("relevance_score", 0.0),
                filename=source.get("filename", ""),
                title=source.get("title", ""),
            )
        )
    conversation.updated_at = func.now()
    if role == "user" and conversation.title == "New Conversation":
        conversation.title = content.strip()[:80] or "New Conversation"
    await db.commit()
    await db.refresh(message)
    return message


async def get_recent_messages(
    db: AsyncSession,
    conversation: Conversation,
    limit: int,
) -> list[dict[str, str]]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .where(Message.role.in_(("user", "assistant")))
        .order_by(Message.created_at.desc())
        .limit(limit * 2)
    )
    messages = list(result.scalars().all())
    messages.reverse()
    return [{"role": m.role, "content": m.content} for m in messages[-limit:]]
