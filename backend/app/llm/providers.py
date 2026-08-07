from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.logging import get_logger
from app.core.security import decrypt_secret
from app.llm.base import (
    BaseLLMProvider,
    ChatMessage,
    LLMAuthError,
    LLMError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
    ProviderConfig,
)
from app.models.llm import LLMProvider as LLMProviderModel

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 120


def classify_http_error(exc: httpx.HTTPStatusError) -> LLMError:
    status = exc.response.status_code
    if status == 401 or status == 403:
        return LLMAuthError(f"Invalid API key or insufficient permissions (HTTP {status}).")
    if status == 429:
        return LLMRateLimitError("LLM API rate limit exceeded.")
    if status >= 500:
        return LLMUnavailableError(f"LLM API temporarily unavailable (HTTP {status}).")
    return LLMError(f"LLM API error (HTTP {status}).")


class OpenAICompatibleProvider(BaseLLMProvider):
    provider_type = "openai_compatible"

    def _build_payload(self, messages: list[ChatMessage], *, stream: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "stream": stream,
        }
        if self.config.extra:
            allowed = {"top_p", "frequency_penalty", "presence_penalty", "stop"}
            for key, value in self.config.extra.items():
                if key in allowed:
                    payload[key] = value
        return payload

    async def _request(self, messages: list[ChatMessage], *, timeout: int, stream: bool) -> httpx.Response:
        timeout_client = httpx.Timeout(timeout, connect=10)
        try:
            async with httpx.AsyncClient(timeout=timeout_client) as client:
                return await client.post(
                    self.build_endpoint(),
                    headers=self.build_headers(),
                    json=self._build_payload(messages, stream=stream),
                )
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"LLM request timed out after {timeout}s.") from exc
        except httpx.ConnectError as exc:
            raise LLMUnavailableError(f"Could not connect to LLM endpoint {self.config.base_url}.") from exc

    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> str:
        self._override(model, temperature, max_tokens)
        response = await self._request(messages, timeout=timeout or DEFAULT_TIMEOUT, stream=False)
        if response.status_code >= 400:
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise classify_http_error(exc) from exc
        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected LLM response shape: {data}") from exc

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> AsyncIterator[str]:
        self._override(model, temperature, max_tokens)
        timeout_client = httpx.Timeout(timeout or DEFAULT_TIMEOUT, connect=10)
        try:
            async with httpx.AsyncClient(timeout=timeout_client) as client:
                async with client.stream(
                    "POST",
                    self.build_endpoint(),
                    headers=self.build_headers(),
                    json=self._build_payload(messages, stream=True),
                ) as response:
                    if response.status_code >= 400:
                        try:
                            response.raise_for_status()
                        except httpx.HTTPStatusError as exc:
                            raise classify_http_error(exc) from exc
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data:"):
                            line = line[len("data:") :].strip()
                        if line == "[DONE]":
                            break
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        choices = chunk.get("choices") or []
                        if not choices:
                            continue
                        delta = choices[0].get("delta") or {}
                        content = delta.get("content")
                        if content:
                            yield content
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"LLM stream timed out after {timeout or DEFAULT_TIMEOUT}s.") from exc
        except httpx.ConnectError as exc:
            raise LLMUnavailableError(f"Could not connect to LLM endpoint {self.config.base_url}.") from exc

    def _override(
        self,
        model: str | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> None:
        if model:
            self.config.model = model
        if temperature is not None:
            self.config.temperature = temperature
        if max_tokens is not None:
            self.config.max_tokens = max_tokens


class OpenRouterProvider(OpenAICompatibleProvider):
    provider_type = "openrouter"

    def build_endpoint(self) -> str:
        base = (self.config.base_url or "https://openrouter.ai/api/v1").rstrip("/")
        return f"{base}/chat/completions"

    def build_headers(self) -> dict[str, str]:
        headers = super().build_headers()
        headers["HTTP-Referer"] = self.config.extra.get("referer", "http://localhost:3000")
        headers["X-Title"] = self.config.extra.get("title", "Postgraduate Information Assistant")
        return headers


class OpenCodeCompatibleProvider(OpenAICompatibleProvider):
    provider_type = "opencode"


class CustomProvider(OpenAICompatibleProvider):
    provider_type = "custom"


def build_provider(model: LLMProviderModel, api_key: str | None = None) -> BaseLLMProvider:
    decrypted = api_key
    if decrypted is None:
        decrypted = decrypt_secret(model.api_key_encrypted)
    config = ProviderConfig(
        name=model.name,
        provider_type=model.provider_type,
        base_url=model.base_url,
        api_key=decrypted,
        model=model.model,
        temperature=model.temperature,
        max_tokens=model.max_tokens,
        timeout=model.timeout,
        extra=model.extra or {},
    )
    mapping = {
        "openrouter": OpenRouterProvider,
        "opencode": OpenCodeCompatibleProvider,
        "custom": CustomProvider,
        "openai_compatible": OpenAICompatibleProvider,
    }
    cls = mapping.get(model.provider_type, OpenAICompatibleProvider)
    return cls(config)
