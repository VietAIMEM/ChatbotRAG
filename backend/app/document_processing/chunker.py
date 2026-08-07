from __future__ import annotations

import re
from dataclasses import dataclass

from app.document_processing.cleaner import detect_section, split_paragraphs
from app.document_processing.parser import ParsedDocument


@dataclass
class Chunk:
    index: int
    text: str
    page_number: int | None = None
    section: str | None = None
    token_count: int = 0


def estimate_tokens(text: str) -> int:
    """Approximate token count. ~4 characters per token plus whitespace words."""
    if not text:
        return 0
    words = len(re.findall(r"\S+", text))
    chars = len(text)
    return max(1, round(words * 0.75 + chars / 12))


def _looks_like_heading(paragraph: str) -> bool:
    stripped = paragraph.strip()
    if not stripped:
        return False
    if stripped.startswith("#"):
        return True
    return len(stripped) <= 70 and not re.search(r"[.?!:;,]$", stripped)


def chunk_document(
    parsed: ParsedDocument,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> list[Chunk]:
    """Paragraph-aware chunking that respects page boundaries and headings.
    Avoids splitting in the middle of paragraphs and carries an overlap
    window of trailing content into the next chunk."""
    chunks: list[Chunk] = []
    current_paras: list[tuple[str, int]] = []  # (paragraph, tokens)
    current_tokens = 0
    overlap_buffer: list[tuple[str, int]] = []  # trailing paragraphs carried over
    current_section: str | None = None
    index_counter = 0

    def flush() -> None:
        nonlocal current_paras, current_tokens, index_counter
        if not current_paras:
            return
        text = "\n\n".join(p for p, _ in current_paras)
        chunks.append(
            Chunk(
                index=index_counter,
                text=text,
                page_number=None,
                section=current_section,
                token_count=estimate_tokens(text),
            )
        )
        index_counter += 1
        current_paras = []
        current_tokens = 0

    def update_overlap(paragraph: str, tokens: int) -> None:
        nonlocal overlap_buffer
        overlap_buffer.append((paragraph, tokens))
        while overlap_buffer and sum(t for _, t in overlap_buffer) > chunk_overlap:
            overlap_buffer.pop(0)

    for page in parsed.pages:
        for paragraph in split_paragraphs(page.text):
            para = paragraph.strip()
            if not para:
                continue
            tokens = estimate_tokens(para)
            if _looks_like_heading(para):
                detected = detect_section(para)
                if detected:
                    current_section = detected
            if current_tokens + tokens > chunk_size and current_paras:
                flush()
                for overlap_para, overlap_tokens in overlap_buffer:
                    current_paras.append((overlap_para, overlap_tokens))
                    current_tokens += overlap_tokens
                overlap_buffer = []
            current_paras.append((para, tokens))
            current_tokens += tokens
            update_overlap(para, tokens)
    flush()

    if not chunks:
        full = parsed.full_text
        chunks.append(
            Chunk(
                index=0,
                text=full,
                page_number=None,
                section=None,
                token_count=estimate_tokens(full),
            )
        )

    # Assign page numbers: chunks take the page number of their first paragraph.
    for chunk in chunks:
        first_para = chunk.text.split("\n\n")[0]
        for page in parsed.pages:
            if first_para in page.text:
                chunk.page_number = page.page_number
                break
    return chunks
