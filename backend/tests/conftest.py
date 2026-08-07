from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_app.db"
os.environ["QDRANT_URL"] = "http://localhost:63333"
os.environ["SECRET_KEY"] = "test-secret-key-for-tests-only"
os.environ["CORS_ORIGINS"] = '["http://localhost:3000"]'
os.environ["DOCUMENT_STORAGE_PATH"] = str(Path(tempfile.mkdtemp()) / "documents")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.admin import Admin

TEST_DB = "sqlite+aiosqlite:///./test_app.db"


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DB)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()
    if Path("./test_app.db").exists():
        Path("./test_app.db").unlink()


@pytest_asyncio.fixture
async def db(engine):
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(engine):
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    from app.services.rate_limit import admin_login_rate_limiter, chat_rate_limiter

    chat_rate_limiter.reset()
    admin_login_rate_limiter.reset()

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with SessionLocal() as session:
        existing = await session.get(Admin, uuid.UUID("00000000-0000-0000-0000-000000000001"))
        if existing is None:
            admin = Admin(
                id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                username="admin",
                password_hash=hash_password("admin12345"),
            )
            session.add(admin)
            await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
