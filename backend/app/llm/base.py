from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

from app.models.llm import LLMProvider as LLMProviderModel


class LLMError(Exception):
    """Base error for all LLM provider failures."""


class LLMTimeoutError(LLMError):
    pass


class LLMRateLimitError(LLMError):
    pass


class LLMAuthError(LLMError):
    pass


class LLMUnavailableError(LLMError):
    pass


@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str


@dataclass
class ProviderConfig:
    name: str = ""
    provider_type: str = "openai_compatible"
    base_url: str = ""
    api_key: str | None = None
    model: str = ""
    temperature: float = 0.2
    max_tokens: int = 1024
    timeout: int = 120
    extra: dict = field(default_factory=dict)


class BaseLLMProvider(ABC):
    provider_type = "base"

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def model(self) -> str:
        return self.config.model

    def build_endpoint(self) -> str:
        base = self.config.base_url.rstrip("/")
        return f"{base}/chat/completions"

    def build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> str:
        """Return a full (non-streaming) completion."""

    @abstractmethod
    def stream(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> AsyncIterator[str]:
        """Yield text deltas as they arrive."""

    async def test_connection(self, *, timeout: int = 30) -> str:
        """Send a minimal request and return a confirmation message."""
        messages = [ChatMessage(role="user", content="ping")]
        return await self.generate(messages, timeout=timeout)

    @staticmethod
    def from_model(model: LLMProviderModel, api_key: str | None = None) -> "BaseLLMProvider":
        from app.llm.providers import build_provider

        return build_provider(model, api_key)
