from __future__ import annotations

import math
import re
from abc import ABC, abstractmethod
from collections import Counter

from app.rag.models import RetrievedChunk


class Reranker(ABC):
    name = "base"

    @abstractmethod
    def rerank(self, query: str, chunks: list[RetrievedChunk], final_k: int) -> list[RetrievedChunk]:
        ...


class ScoreReranker(Reranker):
    """Pure lexical reranker combining vector score with token-overlap signal.

    Works offline (no external model). A cross-encoder reranker can be plugged
    in later behind the same interface via the configurable provider.
    """

    name = "lexical"

    def __init__(self, model: str = "lexical") -> None:
        self.model = model

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9\u00e0-\u00ff]+", text.lower()))

    def rerank(self, query: str, chunks: list[RetrievedChunk], final_k: int) -> list[RetrievedChunk]:
        query_tokens = self._tokens(query)
        if not query_tokens:
            return sorted(chunks, key=lambda c: c.score, reverse=True)[:final_k]

        scored: list[RetrievedChunk] = []
        for chunk in chunks:
            chunk_tokens = self._tokens(chunk.content)
            if not chunk_tokens:
                overlap = 0.0
            else:
                overlap = len(query_tokens & chunk_tokens) / math.sqrt(len(query_tokens) * len(chunk_tokens))
            combined = 0.6 * chunk.score + 0.4 * min(overlap, 1.0)
            chunk.rerank_score = combined
            scored.append(chunk)

        scored.sort(key=lambda c: c.rerank_score or 0.0, reverse=True)
        return scored[:final_k]


class RerankerFactory:
    @staticmethod
    def create(provider: str, model: str) -> Reranker:
        provider = (provider or "local").strip().lower()
        if provider in ("cross_encoder", "cohere", "openai", "custom"):
            # External reranker APIs can be integrated here later. For now all
            # configured providers fall back to the offline lexical reranker.
            return ScoreReranker(model=model or "lexical")
        return ScoreReranker(model=model or "lexical")
