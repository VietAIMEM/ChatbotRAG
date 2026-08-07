from __future__ import annotations

import uuid

import pytest

from app.rag.models import RetrievedChunk


class FakeRetriever:
    def __init__(self, chunks):
        self.chunks = chunks

    async def retrieve(self, query):
        return self.chunks


class FakeGateway:
    def __init__(self, db=None):
        self.calls = []

    async def stream(self, messages, **kwargs):
        for delta in ["The tuition for the Master's program is ", "20 million VND per year."]:
            yield {"provider": "test", "model": "test-model", "delta": delta}

    async def generate(self, messages, **kwargs):
        return "test"


def make_chunk():
    return RetrievedChunk(
        document_id=str(uuid.uuid4()),
        chunk_id="chunk-1",
        point_id="point-1",
        content="Học phí chương trình thạc sĩ là 20 triệu đồng mỗi năm.",
        filename="regulations_2026.pdf",
        title="Quy chế đào tạo 2026",
        document_type="pdf",
        page_number=12,
        section="Học phí",
        is_active=True,
        score=0.91,
        metadata={"year": 2026, "version": "2026"},
    )


def _async_retriever(chunks):
    async def factory(self, config):
        return FakeRetriever(chunks)

    return factory


@pytest.mark.asyncio
async def test_domain_rejection(client, monkeypatch):
    response = await client.post(
        "/api/chat/stream",
        json={"client_id": "test-client-00000001", "question": "Write Python code for a linked list"},
    )
    assert response.status_code == 200
    assert "Sorry, I can only assist with postgraduate" in response.text


@pytest.mark.asyncio
async def test_chat_stream_grounded_answer_with_sources(client, monkeypatch):
    import app.services.chat_service as chat_service

    monkeypatch.setattr(chat_service, "LLMGateway", FakeGateway)
    monkeypatch.setattr(
        chat_service.ChatService,
        "_build_retriever",
        _async_retriever([make_chunk()]),
    )

    response = await client.post(
        "/api/chat/stream",
        json={"client_id": "test-client-00000002", "question": "Học phí thạc sĩ là bao nhiêu?"},
    )
    assert response.status_code == 200
    body = response.text
    assert "The tuition for the Master's program is" in body
    assert "20 million VND per year." in body
    assert "done" in body
    assert "regulations_2026.pdf" in body


@pytest.mark.asyncio
async def test_chat_no_results_when_no_chunks(client, monkeypatch):
    import app.services.chat_service as chat_service

    monkeypatch.setattr(chat_service, "LLMGateway", FakeGateway)
    monkeypatch.setattr(
        chat_service.ChatService,
        "_build_retriever",
        _async_retriever([]),
    )

    response = await client.post(
        "/api/chat/stream",
        json={"client_id": "test-client-00000003", "question": "Học phí thạc sĩ là bao nhiêu?"},
    )
    assert response.status_code == 200
    assert "could not find relevant information" in response.text


@pytest.mark.asyncio
async def test_conversation_lifecycle(client):
    client_id = "test-client-00000004"
    response = await client.post(
        "/api/conversations",
        json={"client_id": client_id, "title": "My conversation"},
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]

    listing = await client.get(f"/api/conversations?client_id={client_id}")
    assert listing.status_code == 200
    assert any(c["session_id"] == session_id for c in listing.json()["items"])

    detail = await client.get(f"/api/conversations/{session_id}?client_id={client_id}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "My conversation"

    deleted = await client.delete(f"/api/conversations/{session_id}?client_id={client_id}")
    assert deleted.status_code == 200

    gone = await client.get(f"/api/conversations/{session_id}?client_id={client_id}")
    assert gone.status_code == 404
