from __future__ import annotations

import asyncio
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.document_processing.chunker import Chunk, chunk_document
from app.document_processing.parser import parse_document
from app.models.document import Document, DocumentChunk
from app.rag.embeddings import EmbeddingProviderFactory
from app.rag.models import RAGConfigData
from app.rag.vector_store import QdrantVectorStore

logger = get_logger(__name__)


def _point_id() -> str:
    return str(uuid.uuid4())


def _chunk_payload(doc: Document, chunk: Chunk, point_id: str) -> dict[str, Any]:
    return {
        "document_id": str(doc.id),
        "chunk_id": point_id,
        "filename": doc.filename,
        "title": doc.title,
        "document_type": doc.document_type,
        "page_number": chunk.page_number,
        "section": chunk.section,
        "category": doc.category,
        "year": doc.year,
        "version": doc.version,
        "department": doc.department,
        "program": doc.program,
        "is_active": doc.is_active,
        "status": "INDEXED",
        "content": chunk.text,
    }


class DocumentIndexer:
    """Runs the document → text → chunks → vectors → Qdrant + PostgreSQL pipeline."""

    def __init__(self, vector_store: QdrantVectorStore, config: RAGConfigData) -> None:
        self.vector_store = vector_store
        self.config = config
        self.embedding = EmbeddingProviderFactory.create(config)

    async def index(self, db: AsyncSession, document: Document) -> Document:
        doc = document
        doc.status = "PROCESSING"
        doc.error_message = None
        await db.commit()

        # 1. Parse
        try:
            parsed = await asyncio.to_thread(
                parse_document, doc.file_path, f".{doc.document_type}"
            )
        except Exception as exc:
            raise RuntimeError(f"Document parsing failed: {exc}") from exc

        # 2. Chunk
        doc.status = "CHUNKING"
        await db.commit()
        chunks: list[Chunk] = await asyncio.to_thread(
            chunk_document,
            parsed,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        if not chunks:
            raise RuntimeError("Chunking produced no chunks.")

        # 3. Embed
        doc.status = "EMBEDDING"
        await db.commit()
        texts = [chunk.text for chunk in chunks]
        try:
            vectors = await self.embedding.embed(texts)
        except Exception as exc:
            raise RuntimeError(f"Embedding generation failed: {exc}") from exc
        if not vectors:
            raise RuntimeError("Embedding generation returned no vectors.")

        # 4. Ensure collection size matches the active embedding model
        await self.vector_store.ensure_collection(len(vectors[0]))

        # 5. Remove old vectors (for re-index / replace) then upsert new ones
        doc.status = "INDEXING"
        await db.commit()
        await self.vector_store.delete_by_document(str(doc.id))

        points: list[dict[str, Any]] = []
        payloads: list[dict[str, Any]] = []
        for chunk, vector in zip(chunks, vectors):
            point_id = _point_id()
            points.append(
                {
                    "id": point_id,
                    "vector": vector,
                    "payload": _chunk_payload(doc, chunk, point_id),
                }
            )
            payloads.append((chunk, point_id))

        await self.vector_store.upsert_points(points)

        # 6. Persist chunk records in PostgreSQL
        await self._replace_chunk_records(db, doc, payloads)

        # 7. Mark indexed
        doc.status = "INDEXED"
        doc.chunk_count = len(chunks)
        doc.error_message = None
        await db.commit()
        logger.info("document_indexed id=%s chunks=%d", doc.id, len(chunks))
        return doc

    async def _replace_chunk_records(
        self,
        db: AsyncSession,
        doc: Document,
        payloads: list[tuple[Chunk, str]],
    ) -> None:
        from sqlalchemy import delete as sa_delete

        await db.execute(sa_delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
        for index, (chunk, point_id) in enumerate(payloads):
            db.add(
                DocumentChunk(
                    document_id=doc.id,
                    chunk_index=index,
                    content=chunk.text,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    point_id=point_id,
                    token_count=chunk.token_count,
                    meta={
                        "document_id": str(doc.id),
                        "title": doc.title,
                        "year": doc.year,
                        "version": doc.version,
                        "is_active": doc.is_active,
                    },
                )
            )
        await db.commit()


async def reindex_document(
    db: AsyncSession,
    document: Document,
    vector_store: QdrantVectorStore,
    config: RAGConfigData,
) -> Document:
    return await DocumentIndexer(vector_store, config).index(db, document)


async def _run_indexing_task(document_id: uuid.UUID) -> None:
    from app.core.database import SessionLocal
    from app.services.rag_config_service import load_rag_config

    async with SessionLocal() as db:
        document = await db.get(Document, document_id)
        if document is None:
            logger.error("indexing_task document_not_found id=%s", document_id)
            return
        try:
            config = await load_rag_config(db)
            vector_store = QdrantVectorStore()
            await DocumentIndexer(vector_store, config).index(db, document)
        except Exception as exc:
            document.status = "FAILED"
            document.error_message = str(exc)[:2000]
            await db.commit()
            logger.error("indexing_task failed id=%s error=%s", document_id, exc)


def start_indexing_task(document_id: uuid.UUID) -> None:
    """Kick off document indexing in the background so the API stays responsive."""
    import asyncio

    asyncio.get_running_loop().create_task(_run_indexing_task(document_id))
