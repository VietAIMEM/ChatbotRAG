from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth as admin_auth
from app.api.v1 import chat, conversations, documents, health, system
from app.api.v1.admin import (
    conversations as admin_conversations,
)
from app.api.v1.admin import dashboard, documents as admin_documents, llm, logs, rag, settings

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(system.router)
api_router.include_router(chat.router)
api_router.include_router(conversations.router)
api_router.include_router(documents.router)

api_router.include_router(admin_auth.router, prefix="/admin")
api_router.include_router(dashboard.router, prefix="/admin")
api_router.include_router(admin_documents.router, prefix="/admin")
api_router.include_router(llm.router, prefix="/admin")
api_router.include_router(rag.router, prefix="/admin")
api_router.include_router(admin_conversations.router, prefix="/admin")
api_router.include_router(logs.router, prefix="/admin")
api_router.include_router(settings.router, prefix="/admin")
