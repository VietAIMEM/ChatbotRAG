from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.settings import PublicSettingsOut
from app.services import settings_service

router = APIRouter(tags=["system"])


@router.get("/public-settings", response_model=PublicSettingsOut)
async def public_settings(
    db: AsyncSession = Depends(get_db),
):
    data = await settings_service.load_public_settings(db)
    return PublicSettingsOut(**data)
