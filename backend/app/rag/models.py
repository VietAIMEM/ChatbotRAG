from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings


@dataclass
class RAGConfigData:
    embedding_provider: str = settings.DEFAULT_EMBEDDING_PROVIDER
    embedding_model: str = settings.DEFAULT_EMBEDDING_MODEL
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    reranker_provider: str = settings.DEFAULT_RERANKER_PROVIDER
    reranker_model: str = settings.DEFAULT_RERANKER_MODEL
    chunk_size: int = settings.DEFAULT_CHUNK_SIZE
    chunk_overlap: int = settings.DEFAULT_CHUNK_OVERLAP
    top_k: int = settings.DEFAULT_TOP_K
    final_k: int = settings.DEFAULT_FINAL_K
    similarity_threshold: float = settings.DEFAULT_SIMILARITY_THRESHOLD
    enable_query_rewrite: bool = settings.DEFAULT_ENABLE_QUERY_REWRITE
    enable_reranker: bool = settings.DEFAULT_ENABLE_RERANKER

    def to_dict(self) -> dict[str, Any]:
        return {
            "embedding_provider": self.embedding_provider,
            "embedding_model": self.embedding_model,
            "embedding_base_url": self.embedding_base_url,
            "embedding_api_key": self.embedding_api_key,
            "reranker_provider": self.reranker_provider,
            "reranker_model": self.reranker_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "top_k": self.top_k,
            "final_k": self.final_k,
            "similarity_threshold": self.similarity_threshold,
            "enable_query_rewrite": self.enable_query_rewrite,
            "enable_reranker": self.enable_reranker,
        }


RAG_CONFIG_KEYS = list(RAGConfigData().to_dict().keys())


@dataclass
class RetrievedChunk:
    document_id: str
    chunk_id: str
    point_id: str
    content: str
    filename: str
    title: str
    document_type: str
    page_number: int | None
    section: str | None
    is_active: bool
    score: float
    rerank_score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
