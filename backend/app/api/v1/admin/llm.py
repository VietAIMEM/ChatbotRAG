from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.core.security import decrypt_secret, encrypt_secret, mask_secret
from app.llm.base import LLMError
from app.models.admin import Admin
from app.models.llm import LLMProvider
from app.schemas.llm import (
    LLMProviderCreate,
    LLMProviderOut,
    LLMProviderUpdate,
    TestProviderResult,
)
from app.services.llm_gateway import LLMGateway

router = APIRouter(prefix="/llm-providers", tags=["admin-llm"])


def _out(provider: LLMProvider) -> LLMProviderOut:
    out = LLMProviderOut.model_validate(provider)
    out.has_api_key = bool(provider.api_key_encrypted)
    out.api_key_masked = mask_secret(decrypt_secret(provider.api_key_encrypted))
    return out


@router.get("", response_model=list[LLMProviderOut])
async def list_providers(
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(LLMProvider).order_by(LLMProvider.priority.asc()))
    return [_out(p) for p in result.scalars().all()]


@router.post("", response_model=LLMProviderOut, status_code=201)
async def create_provider(
    payload: LLMProviderCreate,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    provider = LLMProvider(
        name=payload.name,
        provider_type=payload.provider_type,
        base_url=payload.base_url,
        api_key_encrypted=encrypt_secret(payload.api_key),
        model=payload.model,
        temperature=payload.temperature,
        max_tokens=payload.max_tokens,
        timeout=payload.timeout,
        enabled=payload.enabled,
        priority=payload.priority,
        extra=payload.extra,
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return _out(provider)


@router.put("/{provider_id}", response_model=LLMProviderOut)
async def update_provider(
    provider_id: uuid.UUID,
    payload: LLMProviderUpdate,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    provider = await db.get(LLMProvider, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    data = payload.model_dump(exclude_unset=True)
    if "api_key" in data:
        data["api_key_encrypted"] = encrypt_secret(data.pop("api_key"))
    for key, value in data.items():
        if hasattr(provider, key):
            setattr(provider, key, value)
    await db.commit()
    await db.refresh(provider)
    gateway = LLMGateway(db)
    await gateway.clear_cache()
    return _out(provider)


@router.delete("/{provider_id}")
async def delete_provider(
    provider_id: uuid.UUID,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    provider = await db.get(LLMProvider, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    await db.delete(provider)
    await db.commit()
    gateway = LLMGateway(db)
    await gateway.clear_cache()
    return {"message": "Provider deleted"}


@router.post("/{provider_id}/test", response_model=TestProviderResult)
async def test_provider(
    provider_id: uuid.UUID,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    provider = await db.get(LLMProvider, provider_id)
    if provider is None:
        raise HTTPException(status_code=404, detail="Provider not found")
    from app.llm.providers import build_provider

    llm = build_provider(provider)
    try:
        message = await llm.test_connection()
        return TestProviderResult(
            success=True,
            message="Connection successful." if not message else f"Connection successful: {message[:120]}",
            provider=provider.name,
            model=provider.model,
        )
    except LLMError as exc:
        return TestProviderResult(success=False, message=str(exc), provider=provider.name, model=provider.model)
    except Exception as exc:
        return TestProviderResult(success=False, message=f"Unexpected error: {exc}", provider=provider.name, model=provider.model)
