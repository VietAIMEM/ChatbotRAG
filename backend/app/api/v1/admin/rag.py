from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.schemas.rag import AvailableModel, RAGConfigOut, RAGConfigUpdate
from app.services.rag_config_service import load_rag_config, save_rag_config

router = APIRouter(prefix="/rag", tags=["admin-rag"])

AVAILABLE_EMBEDDING_MODELS = [
    AvailableModel(value="hash-bge-m3-v1", label="Local Hash Embedding (offline, default)"),
    AvailableModel(value="text-embedding-3-small", label="OpenAI text-embedding-3-small"),
    AvailableModel(value="text-embedding-3-large", label="OpenAI text-embedding-3-large"),
    AvailableModel(value="bge-m3", label="BAAI/bge-m3 (via compatible API)"),
]

AVAILABLE_RERANKER_MODELS = [
    AvailableModel(value="lexical", label="Local Lexical Reranker (offline, default)"),
    AvailableModel(value="cross-encoder/ms-marco-MiniLM-L-6-v2", label="Cross-encoder (external)"),
    AvailableModel(value="rerank-v3.5", label="Cohere rerank (external)"),
]


@router.get("/config", response_model=RAGConfigOut)
async def get_config(
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    config = await load_rag_config(db)
    return RAGConfigOut(**config.to_dict())


@router.put("/config", response_model=RAGConfigOut)
async def update_config(
    payload: RAGConfigUpdate,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    config = await save_rag_config(db, payload.model_dump())
    return RAGConfigOut(**config.to_dict())


@router.get("/embedding-models", response_model=list[AvailableModel])
async def list_embedding_models(
    _: Admin = Depends(get_current_admin),
):
    return AVAILABLE_EMBEDDING_MODELS


@router.get("/reranker-models", response_model=list[AvailableModel])
async def list_reranker_models(
    _: Admin = Depends(get_current_admin),
):
    return AVAILABLE_RERANKER_MODELS
