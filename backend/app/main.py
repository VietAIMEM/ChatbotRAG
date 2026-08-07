from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.database import create_storage_dirs
from app.core.logging import get_logger

logger = get_logger(__name__)


async def wait_for_database(retries: int = 30, delay: float = 2.0) -> None:
    from sqlalchemy import text

    from app.core.database import engine

    for attempt in range(1, retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("database_connected")
            return
        except Exception as exc:
            logger.warning("database_unavailable attempt=%s error=%s", attempt, exc)
            await asyncio.sleep(delay)
    logger.error("database_unavailable giving_up")


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_storage_dirs()
    await wait_for_database(retries=30, delay=2.0)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        description=(
            "RAG-powered Postgraduate Information Assistant. Chat without login, "
            "admin dashboard for document management, LLM providers, RAG tuning, "
            "conversations and system logs."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/docs")

    return app


app = create_app()
