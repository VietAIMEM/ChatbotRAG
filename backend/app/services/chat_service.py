from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.llm.base import ChatMessage
from app.models.conversation import Conversation
from app.rag.domain import NO_INFO_MESSAGE, is_postgraduate_question, is_rejection_answer
from app.rag.embeddings import EmbeddingProviderFactory
from app.rag.models import RAGConfigData, RetrievedChunk
from app.rag.prompts import DOMAIN_REJECTION_MESSAGE
from app.rag.query_rewrite import heuristic_rewrite
from app.rag.retrieval import Retriever
from app.rag.rerankers import RerankerFactory
from app.rag.vector_store import QdrantVectorStore
from app.services import conversation_service
from app.services import log_service
from app.services.llm_gateway import LLMGateway
from app.services.rag_config_service import load_rag_config
from app.services.settings_service import load_security

logger = get_logger(__name__)


class ChatService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.gateway = LLMGateway(db)

    async def get_chat_rate_limit(self) -> int:
        security = await load_security(self.db)
        return security.chat_rate_limit_per_minute

    async def _build_retriever(self, config: RAGConfigData) -> Retriever:
        embedding = EmbeddingProviderFactory.create(config)
        vector_store = QdrantVectorStore()
        await vector_store.ensure_collection(embedding.vector_size)
        reranker = RerankerFactory.create(config.reranker_provider, config.reranker_model)
        return Retriever(embedding, vector_store, config, reranker)

    async def stream_answer(self, request: Any) -> AsyncIterator[dict[str, Any]]:
        """Yield SSE-style event dicts for the full chat turn."""
        started = time.monotonic()
        conversation: Conversation = await conversation_service.get_or_create_conversation(
            self.db, request.client_id, request.conversation_id
        )
        await conversation_service.add_message(self.db, conversation, "user", request.question)
        session_id = conversation.session_id

        history = await conversation_service.get_recent_messages(
            self.db, conversation, 8
        )
        history_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)

        # ---- Domain validation (cheap, no LLM/RAG) ----
        if not is_postgraduate_question(request.question, history_text):
            message = await conversation_service.add_message(
                self.db, conversation, "assistant", DOMAIN_REJECTION_MESSAGE
            )
            yield {"type": "start"}
            yield {"type": "delta", "content": DOMAIN_REJECTION_MESSAGE}
            yield {
                "type": "done",
                "conversation_id": session_id,
                "message_id": str(message.id),
                "sources": [],
                "rewritten_query": None,
            }
            await log_service.create_log(
                self.db,
                event_type="domain_rejection",
                conversation_id=session_id,
                question=request.question,
            )
            return

        # ---- RAG retrieval ----
        config = await load_rag_config(self.db)
        rewritten_query = request.question
        if config.enable_query_rewrite and len(history) > 1:
            previous_user = next(
                (m["content"] for m in reversed(history) if m["role"] == "user"),
                None,
            )
            rewritten = heuristic_rewrite(request.question, previous_user)
            if rewritten != request.question:
                rewritten_query = rewritten

        try:
            retriever = await self._build_retriever(config)
            chunks: list[RetrievedChunk] = await retriever.retrieve(rewritten_query)
        except Exception as exc:
            logger.error("retrieval_failed error=%s", exc)
            await log_service.create_log(
                self.db,
                level="ERROR",
                event_type="rag_request",
                conversation_id=session_id,
                question=request.question,
                rewritten_query=rewritten_query,
                status="error",
                error=str(exc),
                latency_ms=(time.monotonic() - started) * 1000,
            )
            yield {"type": "error", "message": "Sorry, the knowledge base is temporarily unavailable. Please try again later."}
            return

        if not chunks:
            message = await conversation_service.add_message(
                self.db, conversation, "assistant", NO_INFO_MESSAGE
            )
            yield {"type": "start"}
            yield {"type": "delta", "content": NO_INFO_MESSAGE}
            yield {
                "type": "done",
                "conversation_id": session_id,
                "message_id": str(message.id),
                "sources": [],
                "rewritten_query": rewritten_query,
            }
            await log_service.create_log(
                self.db,
                event_type="rag_request",
                conversation_id=session_id,
                question=request.question,
                rewritten_query=rewritten_query,
                retrieved_documents=[c.filename for c in chunks],
                status="no_results",
                latency_ms=(time.monotonic() - started) * 1000,
            )
            return

        # ---- Build prompt ----
        from app.rag.pipeline import build_history_text, build_source_records, build_system_prompt

        system_prompt = build_system_prompt(chunks, build_history_text(history[:-1] if history else []))
        messages: list[ChatMessage] = [ChatMessage(role="system", content=system_prompt)]
        for item in history[:-1]:
            messages.append(ChatMessage(role=item["role"], content=item["content"]))
        messages.append(ChatMessage(role="user", content=request.question))

        yield {"type": "start"}
        answer_parts: list[str] = []
        provider_name: str | None = None
        model_name: str | None = None
        try:
            async for event in self.gateway.stream(
                messages,
                temperature=config.temperature if hasattr(config, "temperature") else None,
            ):
                provider_name = event["provider"]
                model_name = event["model"]
                delta = event["delta"]
                answer_parts.append(delta)
                yield {"type": "delta", "content": delta}
        except Exception as exc:
            logger.error("llm_stream_failed error=%s", exc)
            await log_service.create_log(
                self.db,
                level="ERROR",
                event_type="rag_request",
                conversation_id=session_id,
                question=request.question,
                rewritten_query=rewritten_query,
                retrieved_documents=[c.filename for c in chunks],
                retrieved_scores=[c.score for c in chunks],
                reranker_scores=[c.rerank_score for c in chunks],
                llm_provider=provider_name,
                llm_model=model_name,
                status="error",
                error=str(exc),
                latency_ms=(time.monotonic() - started) * 1000,
            )
            yield {"type": "error", "message": "Sorry, I could not generate a response right now. Please try again."}
            return

        answer = "".join(answer_parts).strip()
        sources = build_source_records(chunks)
        if is_rejection_answer(answer):
            sources = []

        assistant_message = await conversation_service.add_message(
            self.db, conversation, "assistant", answer, sources=sources
        )

        yield {
            "type": "done",
            "conversation_id": session_id,
            "message_id": str(assistant_message.id),
            "sources": sources,
            "rewritten_query": rewritten_query if rewritten_query != request.question else None,
        }

        await log_service.create_log(
            self.db,
            event_type="rag_request",
            conversation_id=session_id,
            question=request.question,
            rewritten_query=rewritten_query,
            retrieved_documents=[c.filename for c in chunks],
            retrieved_scores=[c.score for c in chunks],
            reranker_scores=[c.rerank_score for c in chunks],
            selected_sources=[c.chunk_id for c in chunks],
            llm_provider=provider_name,
            llm_model=model_name,
            latency_ms=(time.monotonic() - started) * 1000,
        )
