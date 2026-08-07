from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.llm.base import ChatMessage, LLMError, LLMUnavailableError
from app.llm.providers import build_provider
from app.models.llm import LLMProvider as LLMProviderModel

logger = get_logger(__name__)


class LLMGateway:
    """Provides access to configured LLM providers with automatic fallback."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._cache: list[tuple[LLMProviderModel, object]] | None = None

    async def enabled_providers(self) -> list[tuple[LLMProviderModel, object]]:
        if self._cache is None:
            result = await self.db.execute(
                select(LLMProviderModel)
                .where(LLMProviderModel.enabled.is_(True))
                .order_by(LLMProviderModel.priority.asc(), LLMProviderModel.created_at.asc())
            )
            models = list(result.scalars().all())
            self._cache = [(m, build_provider(m)) for m in models]
        return self._cache

    async def clear_cache(self) -> None:
        self._cache = None

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> tuple[str, str, str]:
        """Generate a full completion. Returns (provider_name, model, text)."""
        providers = await self.enabled_providers()
        if not providers:
            raise LLMUnavailableError("No enabled LLM providers are configured. Please add one in Admin → LLM Providers.")

        last_error: Exception | None = None
        for model, provider in providers:
            try:
                text = await provider.generate(
                    messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
                return model.name, provider.model, text
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "llm_fallback provider=%s model=%s error=%s",
                    model.name,
                    provider.model,
                    exc,
                )
        raise last_error or LLMUnavailableError("All LLM providers failed.")

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> AsyncIterator[dict]:
        """Stream deltas with fallback. Yields {"provider", "model", "delta"}.
        On total failure raises the last error after exhausting providers."""
        providers = await self.enabled_providers()
        if not providers:
            raise LLMUnavailableError("No enabled LLM providers are configured. Please add one in Admin → LLM Providers.")

        last_error: Exception | None = None
        for model, provider in providers:
            agen = provider.stream(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            started = False
            try:
                first = await agen.__anext__()
                started = True
                yield {"provider": model.name, "model": provider.model, "delta": first}
                async for delta in agen:
                    yield {"provider": model.name, "model": provider.model, "delta": delta}
                return
            except StopAsyncIteration:
                last_error = LLMError(f"Provider '{model.name}' returned an empty response.")
                logger.warning("llm_empty_response provider=%s", model.name)
            except Exception as exc:
                last_error = exc
                logger.warning("llm_fallback provider=%s model=%s error=%s", model.name, provider.model, exc)
            finally:
                if started:
                    await asyncio.to_thread(lambda: None)  # ensure cleanup ordering
        raise last_error or LLMUnavailableError("All LLM providers failed.")
