from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.models.system_log import SystemLog
from app.schemas.log import DashboardStats, SystemLogOut

router = APIRouter(prefix="/dashboard", tags=["admin-dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    total_docs = (await db.execute(select(func.count()).select_from(Document))).scalar_one()
    indexed = (
        await db.execute(
            select(func.count()).select_from(Document).where(Document.status == "INDEXED")
        )
    ).scalar_one()
    processing = (
        await db.execute(
            select(func.count())
            .select_from(Document)
            .where(Document.status.in_(["UPLOADING", "PROCESSING", "CHUNKING", "EMBEDDING", "INDEXING"]))
        )
    ).scalar_one()
    failed = (
        await db.execute(
            select(func.count()).select_from(Document).where(Document.status == "FAILED")
        )
    ).scalar_one()
    total_conversations = (await db.execute(select(func.count()).select_from(Conversation))).scalar_one()
    total_messages = (await db.execute(select(func.count()).select_from(Message))).scalar_one()
    rag_queries = (
        await db.execute(
            select(func.count())
            .select_from(SystemLog)
            .where(SystemLog.event_type == "rag_request")
        )
    ).scalar_one()
    llm_requests = rag_queries
    recent = (
        await db.execute(select(SystemLog).order_by(SystemLog.timestamp.desc()).limit(10))
    ).scalars().all()

    return DashboardStats(
        total_documents=int(total_docs),
        indexed_documents=int(indexed),
        processing_documents=int(processing),
        failed_documents=int(failed),
        total_conversations=int(total_conversations),
        total_messages=int(total_messages),
        llm_requests=int(llm_requests),
        rag_queries=int(rag_queries),
        recent_activity=[SystemLogOut.model_validate(r) for r in recent],
    )
