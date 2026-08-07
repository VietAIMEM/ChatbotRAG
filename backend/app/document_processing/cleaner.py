from __future__ import annotations

import re
from typing import Any


def clean_text(text: str) -> str:
    """Clean extracted text: strip control chars, normalize whitespace,
    remove page-header/footer junk heuristically."""
    if not text:
        return ""
    # Remove null bytes and other control characters except newline/tab.
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    # Fix common mojibake for Vietnamese.
    text = (
        text.replace("â€œ", '"')
        .replace("â€", '"')
        .replace("â€™", "'")
        .replace("Ã", "à")
        .replace("Ã©", "é")
        .replace("Ã¨", "è")
        .replace("Ã¬", "ì")
    )
    # Normalize line endings.
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # Collapse 3+ blank lines.
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Trim lines that are only page numbers (e.g. "12", "- 5 -", "Page 3").
    lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if re.fullmatch(r"(\d{1,4}|-\s*\d{1,4}\s*-|Page\s+\d+|Trang\s+\d+)", stripped, re.IGNORECASE):
            continue
        lines.append(line)
    text = "\n".join(lines)
    return text.strip()


def split_paragraphs(text: str) -> list[str]:
    """Split cleaned text into logical paragraphs, preserving headings."""
    blocks = re.split(r"\n\s*\n", text)
    paragraphs: list[str] = []
    for block in blocks:
        block = block.strip()
        if block:
            paragraphs.append(block)
    return paragraphs


def detect_section(line: str) -> str | None:
    """Best-effort heading detection for section tracking."""
    stripped = line.strip()
    if not stripped:
        return None
    if stripped.startswith("#"):
        return re.sub(r"^#+\s*", "", stripped)
    if len(stripped) <= 70 and not re.search(r"[.?!:;,]$", stripped) and not re.search(r"\d{2,}", stripped):
        return stripped
    return None
