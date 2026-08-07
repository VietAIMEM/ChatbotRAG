from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_log import SystemLog
from app.schemas.log import SystemLogOut


async def create_log(
    db: AsyncSession,
    *,
    level: str = "INFO",
    event_type: str,
    conversation_id: str | None = None,
    question: str | None = None,
    rewritten_query: str | None = None,
    retrieved_documents: Any = None,
    retrieved_scores: Any = None,
    reranker_scores: Any = None,
    selected_sources: Any = None,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    latency_ms: float | None = None,
    status: str = "ok",
    error: str | None = None,
    details: Any = None,
) -> SystemLog:
    entry = SystemLog(
        level=level,
        event_type=event_type,
        conversation_id=conversation_id,
        question=question,
        rewritten_query=rewritten_query,
        retrieved_documents=retrieved_documents,
        retrieved_scores=retrieved_scores,
        reranker_scores=reranker_scores,
        selected_sources=selected_sources,
        llm_provider=llm_provider,
        llm_model=llm_model,
        latency_ms=latency_ms,
        status=status,
        error=(error or "")[:4000] if error else None,
        details=details,
    )
    db.add(entry)
    await db.commit()
    return entry


async def list_logs(
    db: AsyncSession,
    *,
    limit: int = 100,
    offset: int = 0,
    event_type: str | None = None,
    level: str | None = None,
) -> tuple[list[SystemLogOut], int]:
    stmt = select(SystemLog)
    count_stmt = select(func.count()).select_from(SystemLog)
    if event_type:
        stmt = stmt.where(SystemLog.event_type == event_type)
        count_stmt = count_stmt.where(SystemLog.event_type == event_type)
    if level:
        stmt = stmt.where(SystemLog.level == level)
        count_stmt = count_stmt.where(SystemLog.level == level)
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(SystemLog.timestamp.desc()).offset(offset).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return [SystemLogOut.model_validate(r) for r in rows], int(total)
