from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod
from collections import Counter
from typing import Any

import httpx

from app.core.logging import get_logger
from app.rag.models import RAGConfigData

logger = get_logger(__name__)

HASH_VECTOR_SIZE = 768


class EmbeddingError(Exception):
    pass


class EmbeddingProvider(ABC):
    """Abstraction over embedding models used by the RAG pipeline."""

    name = "base"
    vector_size: int = HASH_VECTOR_SIZE

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    async def embed_query(self, text: str) -> list[float]:
        result = await self.embed([text])
        return result[0]


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0:
        return vec
    return [v / norm for v in vec]


class HashEmbeddingProvider(EmbeddingProvider):
    """Deterministic, dependency-free embedding based on character n-grams.

    Used as the default local provider so the application runs out of the box
    without downloading model weights. It captures enough lexical signal for
    retrieval on education-domain text. Admin can switch to an
    OpenAI-compatible embedding API for higher quality.
    """

    name = "local"

    def __init__(self, model: str = "hash-bge-m3-v1", vector_size: int = HASH_VECTOR_SIZE) -> None:
        self.model = model
        self.vector_size = vector_size

    def _hashes(self, text: str) -> list[int]:
        normalized = re.sub(r"\s+", " ", text.lower())
        grams: list[str] = []
        for n in (2, 3, 4):
            grams.extend(normalized[i : i + n] for i in range(len(normalized) - n + 1))
        if not grams:
            grams = [normalized]
        digest = hashlib.sha256(f"{self.model}:{normalized}".encode("utf-8")).hexdigest()
        grams.append(digest)
        return [int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16) % self.vector_size for g in grams]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            counts: Counter[int] = Counter()
            for idx in self._hashes(text):
                counts[idx] += 1
            vec = [0.0] * self.vector_size
            for idx, count in counts.items():
                vec[idx] = 1.0 + math.log(count)
            vectors.append(_normalize(vec))
        return vectors


class OpenAICompatibleEmbeddingProvider(EmbeddingProvider):
    name = "openai_compatible"

    def __init__(self, model: str = "text-embedding-3-small", base_url: str = "", api_key: str = "") -> None:
        self.model = model
        self.base_url = (base_url or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise EmbeddingError("Embedding API key is not configured.")
        payload: dict[str, Any] = {"model": self.model, "input": texts}
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(f"{self.base_url}/embeddings", json=payload, headers=headers)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise EmbeddingError(f"Embedding API error: HTTP {exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise EmbeddingError(f"Embedding API error: {exc}") from exc
        data = response.json()
        try:
            items = data["data"]
            vectors = [item["embedding"] for item in items]
        except (KeyError, TypeError) as exc:
            raise EmbeddingError(f"Unexpected embedding API response: {data}") from exc
        if vectors:
            self.vector_size = len(vectors[0])
        return [_normalize(vec) for vec in vectors]


class EmbeddingProviderFactory:
    @staticmethod
    def create(config: RAGConfigData) -> EmbeddingProvider:
        provider = (config.embedding_provider or "local").strip().lower()
        model = config.embedding_model or "hash-bge-m3-v1"
        if provider in ("openai_compatible", "openai"):
            return OpenAICompatibleEmbeddingProvider(
                model=model,
                base_url=config.embedding_base_url,
                api_key=config.embedding_api_key,
            )
        if provider in ("custom",):
            return OpenAICompatibleEmbeddingProvider(
                model=model,
                base_url=config.embedding_base_url,
                api_key=config.embedding_api_key,
            )
        return HashEmbeddingProvider(model=model)
