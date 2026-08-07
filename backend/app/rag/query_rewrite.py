from __future__ import annotations

import re
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

_FOLLOW_UP_MARKERS = (
    "how much", "what about", "what is the cost", "how about", "it", "this",
    "that", "them", "there", "their", "they", "those", "then", "when",
    "why", "which", "who", "how long", "how many", "là bao nhiêu", "thế nào",
    "như thế nào", "nó", "về nó", "chi phí", "mức phí", "bao nhiêu",
)


def is_follow_up(question: str) -> bool:
    q = question.strip().lower()
    return len(q.split()) <= 8 or any(marker in q for marker in _FOLLOW_UP_MARKERS)


def _topic_from_previous_question(previous_question: str) -> str:
    return previous_question.strip()


def heuristic_rewrite(question: str, previous_question: str | None) -> str:
    """Rewrite a short follow-up into a self-contained query using the previous
    user question as context. Cheap and does not require an LLM call."""
    if not previous_question or not is_follow_up(question):
        return question
    return f"{question.strip()} (in the context of: {_topic_from_previous_question(previous_question)})"


def rewrite_with_llm(
    llm_generate: Any,
    question: str,
    conversation_history: list[dict[str, str]],
) -> str | None:
    """Rewrite the user question into a standalone retrieval query using the LLM.
    Returns None on failure so the caller can fall back to the heuristic."""
    if not conversation_history:
        return None
    try:
        history_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in conversation_history[-6:]
        )
        from app.rag.prompts import QUERY_REWRITE_PROMPT

        prompt = QUERY_REWRITE_PROMPT.format(
            history=history_text, question=question
        )
        rewritten = re.sub(r"\s+", " ", llm_generate([{"role": "user", "content": prompt}]).strip())
        if rewritten:
            logger.info("rewritten_query=%s", rewritten)
            return rewritten
    except Exception as exc:  # pragma: no cover
        logger.warning("query rewrite failed: %s", exc)
    return None
