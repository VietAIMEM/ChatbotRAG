from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.models.admin import Admin
from app.schemas.settings import SettingsOut, SettingsUpdate
from app.services import settings_service

router = APIRouter(prefix="/settings", tags=["admin-settings"])


@router.get("", response_model=SettingsOut)
async def get_settings(
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    general = await settings_service.load_general(db)
    security = await settings_service.load_security(db)
    metadata = await settings_service.load_metadata(db)
    return SettingsOut(general=general, security=security, metadata=metadata)


@router.put("", response_model=SettingsOut)
async def update_settings(
    payload: SettingsUpdate,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if payload.general:
        general = await settings_service.save_general(db, payload.general.model_dump())
    else:
        general = await settings_service.load_general(db)
    if payload.security:
        security = await settings_service.save_security(db, payload.security.model_dump())
    else:
        security = await settings_service.load_security(db)
    if payload.metadata:
        metadata = await settings_service.save_metadata(db, payload.metadata.model_dump())
    else:
        metadata = await settings_service.load_metadata(db)
    return SettingsOut(general=general, security=security, metadata=metadata)
