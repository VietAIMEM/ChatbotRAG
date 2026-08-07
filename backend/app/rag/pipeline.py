from __future__ import annotations

from app.rag.models import RetrievedChunk
from app.rag.prompts import RAG_SYSTEM_PROMPT


def build_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved chunks into a numbered context block with citation ids."""
    blocks: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        source = chunk.title or chunk.filename
        page = f", page {chunk.page_number}" if chunk.page_number else ""
        blocks.append(
            f"[{idx}] Document: {source}{page}\n"
            f"Year: {chunk.metadata.get('year') or 'N/A'}\n"
            f"Version: {chunk.metadata.get('version') or 'N/A'}\n"
            f"Active: {chunk.is_active}\n"
            f"Content:\n{chunk.content.strip()}"
        )
    return "\n\n---\n\n".join(blocks)


def build_system_prompt(chunks: list[RetrievedChunk], history_text: str) -> str:
    context = build_context(chunks)
    return RAG_SYSTEM_PROMPT.format(context=context, history=history_text or "(no previous messages)")


def build_source_records(chunks: list[RetrievedChunk]) -> list[dict]:
    """Build source records used for the chat API response and stored in
    message_sources. Deduplication for display happens on the frontend."""
    records: list[dict] = []
    seen: set[str] = set()
    for chunk in chunks:
        key = (str(chunk.document_id), chunk.page_number or -1)
        if key in seen:
            continue
        seen.add(key)
        records.append(
            {
                "document_id": chunk.document_id,
                "filename": chunk.filename,
                "title": chunk.title or chunk.filename,
                "document_type": chunk.document_type,
                "page_number": chunk.page_number,
                "chunk_id": chunk.chunk_id,
                "relevance_score": round(chunk.rerank_score or chunk.score, 4),
                "download_url": f"/api/documents/{chunk.document_id}/download",
                "view_url": f"/api/documents/{chunk.document_id}/view",
            }
        )
    return records


def build_history_text(messages: list[dict[str, str]]) -> str:
    return "\n".join(f"{m['role']}: {m['content']}" for m in messages)
