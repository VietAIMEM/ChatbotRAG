from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.document import Document
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


async def _get_document(db: AsyncSession, document_id: uuid.UUID) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/{document_id}/download")
async def download_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    document = await _get_document(db, document_id)
    path = document_service.safe_document_path(document)
    return FileResponse(
        path,
        filename=document.filename,
        media_type=document_service.guess_content_type(document),
        content_disposition_type="attachment",
    )


@router.get("/{document_id}/view")
async def view_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    document = await _get_document(db, document_id)
    path = document_service.safe_document_path(document)
    if document.document_type == "pdf":
        return FileResponse(
            path,
            filename=document.filename,
            media_type="application/pdf",
            content_disposition_type="inline",
        )
    return FileResponse(
        path,
        filename=document.filename,
        media_type=document_service.guess_content_type(document),
        content_disposition_type="attachment",
    )
