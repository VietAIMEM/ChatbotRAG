from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_chat_rate_limit
from app.core.database import get_db
from app.schemas.chat import ChatRequest
from app.services.chat_service import ChatService

router = APIRouter(tags=["chat"])

SSE_HEADERS = {
    "Cache-Control": "no-cache",
    "Connection": "keep-alive",
    "X-Accel-Buffering": "no",
}


@router.post("/chat/stream")
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await check_chat_rate_limit(request)
    service = ChatService(db)

    async def event_stream():
        try:
            async for event in service.stream_answer(payload):
                yield f"data: {json.dumps(event, default=str)}\n\n"
        except Exception as exc:  # pragma: no cover
            yield f"data: {json.dumps({'type': 'error', 'message': 'Unexpected server error. Please try again.'}, default=str)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=SSE_HEADERS)
