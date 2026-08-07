from __future__ import annotations

import asyncio
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.core.logging import get_logger
from app.rag.models import RetrievedChunk

logger = get_logger(__name__)


class VectorStoreError(Exception):
    pass


class QdrantVectorStore:
    def __init__(self, url: str = settings.QDRANT_URL, collection: str = settings.QDRANT_COLLECTION) -> None:
        self.client = QdrantClient(url=url)
        self.collection = collection

    async def _run(self, fn: Any) -> Any:
        return await asyncio.to_thread(fn)

    def _exists(self) -> bool:
        return self.client.collection_exists(self.collection)

    async def ensure_collection(self, vector_size: int) -> None:
        def _do() -> None:
            if self.client.collection_exists(self.collection):
                info = self.client.get_collection(self.collection)
                configured = info.config.params.vectors.size
                if configured != vector_size:
                    logger.warning(
                        "Collection %s has size %s, active embedding size is %s. Recreating collection.",
                        self.collection,
                        configured,
                        vector_size,
                    )
                    self.client.recreate_collection(
                        collection_name=self.collection,
                        vectors_config=qmodels.VectorParams(
                            size=vector_size, distance=qmodels.Distance.COSINE
                        ),
                    )
                return
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=qmodels.VectorParams(size=vector_size, distance=qmodels.Distance.COSINE),
            )

        try:
            await self._run(_do)
        except Exception as exc:
            raise VectorStoreError(f"Failed to initialize Qdrant collection: {exc}") from exc

    async def upsert_points(self, points: list[dict[str, Any]]) -> None:
        def _do() -> None:
            self.client.upsert(
                collection_name=self.collection,
                points=[
                    qmodels.PointStruct(
                        id=point["id"],
                        vector=point["vector"],
                        payload=point["payload"],
                    )
                    for point in points
                ],
            )

        try:
            await self._run(_do)
        except Exception as exc:
            raise VectorStoreError(f"Qdrant upsert failed: {exc}") from exc

    async def delete_by_document(self, document_id: str) -> list[str]:
        """Delete all points for a document, returning their point ids."""

        def _do() -> list[str]:
            from qdrant_client import models as m

            result = self.client.scroll(
                collection_name=self.collection,
                scroll_filter=m.Filter(
                    must=[m.FieldCondition(key="document_id", match=m.MatchValue(value=document_id))]
                ),
                limit=10000,
                with_payload=False,
            )
            points, _ = result
            ids = [p.id for p in points]
            if ids:
                self.client.delete(
                    collection_name=self.collection,
                    points_selector=m.FilterSelector(
                        filter=m.Filter(
                            must=[
                                m.FieldCondition(
                                    key="document_id", match=m.MatchValue(value=document_id)
                                )
                            ]
                        )
                    ),
                )
            return ids

        try:
            return await self._run(_do)
        except Exception as exc:
            raise VectorStoreError(f"Qdrant delete failed: {exc}") from exc

    async def search(
        self,
        vector: list[float],
        *,
        top_k: int,
        threshold: float,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievedChunk]:
        def _do() -> list[RetrievedChunk]:
            must: list[Any] = []
            if filters:
                for key, value in filters.items():
                    if isinstance(value, list):
                        must.append(
                            qmodels.FieldCondition(key=key, match=qmodels.MatchAny(any=value))
                        )
                    else:
                        must.append(qmodels.FieldCondition(key=key, match=qmodels.MatchValue(value=value)))
            result = self.client.query_points(
                collection_name=self.collection,
                query=vector,
                limit=top_k,
                score_threshold=threshold,
                query_filter=qmodels.Filter(must=must) if must else None,
                with_payload=True,
            )
            chunks: list[RetrievedChunk] = []
            for hit in result.points:
                payload = hit.payload or {}
                chunks.append(
                    RetrievedChunk(
                        document_id=str(payload.get("document_id", "")),
                        chunk_id=str(payload.get("chunk_id", "")),
                        point_id=str(hit.id),
                        content=str(payload.get("content", "")),
                        filename=str(payload.get("filename", "")),
                        title=str(payload.get("title", "")),
                        document_type=str(payload.get("document_type", "")),
                        page_number=payload.get("page_number"),
                        section=payload.get("section"),
                        is_active=bool(payload.get("is_active", True)),
                        score=float(hit.score or 0.0),
                        metadata=dict(payload),
                    )
                )
            return chunks

        try:
            return await self._run(_do)
        except Exception as exc:
            raise VectorStoreError(f"Qdrant search failed: {exc}") from exc

    async def set_payload_by_document(self, document_id: str, payload: dict[str, Any]) -> None:
        def _do() -> None:
            self.client.set_payload(
                collection_name=self.collection,
                payload=payload,
                points=qmodels.FilterSelector(
                    filter=qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="document_id", match=qmodels.MatchValue(value=document_id)
                            )
                        ]
                    )
                ),
            )

        try:
            await self._run(_do)
        except Exception as exc:
            raise VectorStoreError(f"Qdrant set_payload failed: {exc}") from exc

    async def health_check(self) -> bool:
        try:
            await self._run(self.client.get_collections)
            return True
        except Exception:
            return False
