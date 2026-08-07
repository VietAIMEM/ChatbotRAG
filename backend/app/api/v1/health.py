from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings
from app.rag.vector_store import QdrantVectorStore

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    import asyncio

    from app.core.database import engine

    db_ok = True
    qdrant_ok = True
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_ok = False
    try:
        qdrant_ok = await QdrantVectorStore().health_check()
    except Exception:
        qdrant_ok = False
    return {
        "status": "ok" if (db_ok and qdrant_ok) else "degraded",
        "app": settings.APP_NAME,
        "database": "ok" if db_ok else "error",
        "qdrant": "ok" if qdrant_ok else "error",
    }
