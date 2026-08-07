from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.schemas.log import SystemLogListResponse
from app.services import log_service

router = APIRouter(prefix="/logs", tags=["admin-logs"])


@router.get("", response_model=SystemLogListResponse)
async def list_logs(
    event_type: str | None = Query(None, max_length=64),
    level: str | None = Query(None, max_length=16),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    items, total = await log_service.list_logs(
        db, limit=limit, offset=offset, event_type=event_type, level=level
    )
    return SystemLogListResponse(items=items, total=total)
