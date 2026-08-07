from __future__ import annotations

import json

import httpx
import pytest

from app.llm.base import ChatMessage, LLMRateLimitError, ProviderConfig
from app.llm.providers import OpenAICompatibleProvider

SSE_BODY = (
    'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n'
    'data: {"choices":[{"delta":{"content":" world"}}]}\n\n'
    "data: [DONE]\n\n"
)


def make_client(handler) -> None:
    real_async_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        return real_async_client(transport=httpx.MockTransport(handler), timeout=kwargs.get("timeout"))

    return factory


def sse_response(request: httpx.Request) -> httpx.Response:
    payload = json.loads(request.content.decode("utf-8"))
    assert payload["stream"] is True
    return httpx.Response(
        200,
        text=SSE_BODY,
        headers={"Content-Type": "text/event-stream"},
    )


def json_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={"choices": [{"message": {"content": "complete answer"}}]},
    )


def rate_limit_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(429, json={"error": {"message": "rate limited"}})


@pytest.mark.asyncio
async def test_stream_yields_deltas(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", make_client(sse_response))

    provider = OpenAICompatibleProvider(ProviderConfig(base_url="https://example.com/v1", api_key="test-key"))
    messages = [ChatMessage(role="user", content="hi")]
    deltas = [delta async for delta in provider.stream(messages, timeout=5)]
    assert deltas == ["Hello", " world"]


@pytest.mark.asyncio
async def test_generate_returns_content(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", make_client(json_response))

    provider = OpenAICompatibleProvider(ProviderConfig(base_url="https://example.com/v1", api_key="test-key"))
    text = await provider.generate([ChatMessage(role="user", content="hi")], timeout=5)
    assert text == "complete answer"


@pytest.mark.asyncio
async def test_stream_raises_rate_limit_error(monkeypatch):
    monkeypatch.setattr(httpx, "AsyncClient", make_client(rate_limit_response))

    provider = OpenAICompatibleProvider(ProviderConfig(base_url="https://example.com/v1", api_key="test-key"))
    agen = provider.stream([ChatMessage(role="user", content="hi")], timeout=5)
    with pytest.raises(LLMRateLimitError):
        await agen.__anext__()
