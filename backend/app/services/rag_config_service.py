from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rag import RAGConfig
from app.rag.models import RAGConfigData, RAG_CONFIG_KEYS


async def load_rag_config(db: AsyncSession) -> RAGConfigData:
    result = await db.execute(select(RAGConfig))
    rows = {row.key: row.value for row in result.scalars().all()}
    data = RAGConfigData()
    for key in RAG_CONFIG_KEYS:
        if key in rows:
            setattr(data, key, rows[key])
    return data


async def save_rag_config(db: AsyncSession, values: dict) -> RAGConfigData:
    for key, value in values.items():
        if key not in RAG_CONFIG_KEYS:
            continue
        row = await db.get(RAGConfig, key)
        if row is None:
            db.add(RAGConfig(key=key, value=value))
        else:
            row.value = value
    await db.commit()
    return await load_rag_config(db)
