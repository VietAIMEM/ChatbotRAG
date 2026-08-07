from __future__ import annotations

from app.core.logging import get_logger
from app.rag.embeddings import EmbeddingProvider
from app.rag.models import RAGConfigData, RetrievedChunk
from app.rag.rerankers import Reranker
from app.rag.vector_store import QdrantVectorStore

logger = get_logger(__name__)


class Retriever:
    def __init__(
        self,
        embedding: EmbeddingProvider,
        vector_store: QdrantVectorStore,
        config: RAGConfigData,
        reranker: Reranker,
    ) -> None:
        self.embedding = embedding
        self.vector_store = vector_store
        self.config = config
        self.reranker = reranker

    async def retrieve(self, query: str) -> list[RetrievedChunk]:
        vector = await self.embedding.embed_query(query)
        chunks = await self.vector_store.search(
            vector,
            top_k=self.config.top_k,
            threshold=self.config.similarity_threshold,
            filters={"is_active": True, "status": "INDEXED"},
        )
        if self.config.enable_reranker and chunks:
            chunks = self.reranker.rerank(query, chunks, self.config.final_k)
        else:
            chunks = chunks[: self.config.final_k]
        logger.info(
            "retrieval query=%s top_k=%s final_k=%s retrieved=%s",
            query,
            self.config.top_k,
            self.config.final_k,
            len(chunks),
        )
        return chunks
