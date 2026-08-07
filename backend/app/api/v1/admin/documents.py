from __future__ import annotations

import asyncio
import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.database import get_db
from app.document_processing.indexer import start_indexing_task
from app.document_processing.parser import SUPPORTED_EXTENSIONS, parse_document
from app.models.admin import Admin
from app.models.document import Document
from app.schemas.document import (
    DocumentListResponse,
    DocumentOut,
    DocumentUpdate,
    MetadataExtractionResult,
    UploadResult,
)
from app.services import document_service, metadata_extractor
from app.services.document_service import DocumentValidationError

router = APIRouter(prefix="/documents", tags=["admin-documents"])


def _doc_out(document: Document) -> DocumentOut:
    return document_service.build_document_out(document)


async def _get_document(db: AsyncSession, document_id: uuid.UUID) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    status_filter: str | None = Query(None, alias="status"),
    q: str | None = Query(None, max_length=255),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Document)
    count_stmt = select(func.count()).select_from(Document)
    if status_filter:
        stmt = stmt.where(Document.status == status_filter)
        count_stmt = count_stmt.where(Document.status == status_filter)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(Document.filename.ilike(like) | Document.title.ilike(like))
        count_stmt = count_stmt.where(Document.filename.ilike(like) | Document.title.ilike(like))
    total = (await db.execute(count_stmt)).scalar_one()
    stmt = stmt.order_by(Document.created_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    items = [_doc_out(d) for d in rows]
    return DocumentListResponse(items=items, total=int(total))


@router.post("/extract-metadata", response_model=MetadataExtractionResult)
async def extract_document_metadata(
    file: UploadFile = File(...),
    use_llm: bool = Query(False),
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Analyze an uploaded file and return detected metadata without saving it."""
    filename = file.filename or "document"
    ext = document_service.get_extension(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext or 'unknown'}'. Supported: .pdf, .doc, .docx, .txt, .md.",
        )
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    target = document_service.storage_dir() / f"_extract_{uuid.uuid4().hex}{ext}"
    try:
        target.write_bytes(content)
        parsed = await asyncio.to_thread(parse_document, str(target), ext)
        return await metadata_extractor.extract_metadata(
            db,
            filename=filename,
            parsed=parsed,
            file_path=str(target),
            extension=ext,
            use_llm=use_llm,
        )
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=400, detail=f"Could not extract text from the file: {exc}") from exc
    finally:
        target.unlink(missing_ok=True)


@router.post("", response_model=UploadResult)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
    category: str | None = Form(None),
    year: int | None = Form(None),
    version: str | None = Form(None),
    department: str | None = Form(None),
    program: str | None = Form(None),
    language: str | None = Form(None),
    effective_date: date | None = Form(None),
    expiration_date: date | None = Form(None),
    auto_index: bool = Form(True),
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    metadata = {
        "title": title,
        "description": description,
        "category": category,
        "year": year,
        "version": version,
        "department": department,
        "program": program,
        "language": language,
        "effective_date": effective_date,
        "expiration_date": expiration_date,
    }
    try:
        document, _ = await document_service.store_uploaded_file(db, file, metadata=metadata)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if auto_index:
        start_indexing_task(document.id)
        return UploadResult(
            document=_doc_out(document),
            message="Document uploaded. Indexing has started.",
        )
    document.status = "DRAFT"
    await db.commit()
    await db.refresh(document)
    return UploadResult(
        document=_doc_out(document),
        message="Document saved as draft. Review the metadata and index it when ready.",
    )


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: uuid.UUID,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    document = await _get_document(db, document_id)
    return _doc_out(document)


@router.put("/{document_id}", response_model=DocumentOut)
async def update_document(
    document_id: uuid.UUID,
    payload: DocumentUpdate,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    document = await _get_document(db, document_id)
    document = await document_service.update_document(db, document, payload.model_dump(exclude_none=True))
    # Keep Qdrant payload is_active in sync when toggled.
    if payload.is_active is not None and document.status == "INDEXED":
        from app.rag.vector_store import QdrantVectorStore

        try:
            await QdrantVectorStore().set_payload_by_document(
                str(document.id), {"is_active": bool(payload.is_active)}
            )
        except Exception:
            pass
    await db.refresh(document)
    return _doc_out(document)


@router.post("/{document_id}/replace", response_model=DocumentOut)
async def replace_document(
    document_id: uuid.UUID,
    file: UploadFile = File(...),
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    document = await _get_document(db, document_id)
    try:
        new_document, _ = await document_service.store_uploaded_file(
            db,
            file,
            metadata={
                "title": document.title,
                "description": document.description,
                "category": document.category,
                "year": document.year,
                "version": document.version,
                "department": document.department,
                "program": document.program,
                "language": document.language,
                "effective_date": document.effective_date,
                "expiration_date": document.expiration_date,
            },
        )
    except DocumentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Remove the old document (file + vectors + records), then index the new one.
    old = document
    old_file = document_service.safe_document_path(old)
    if old_file.exists():
        old_file.unlink(missing_ok=True)
    from app.rag.vector_store import QdrantVectorStore

    await QdrantVectorStore().delete_by_document(str(old.id))
    from sqlalchemy import delete as sa_delete

    from app.models.conversation import MessageSource
    from app.models.document import DocumentChunk

    await db.execute(sa_delete(MessageSource).where(MessageSource.document_id == old.id))
    await db.execute(sa_delete(DocumentChunk).where(DocumentChunk.document_id == old.id))
    await db.delete(old)
    await db.commit()

    start_indexing_task(new_document.id)
    return _doc_out(new_document)


@router.post("/{document_id}/re-extract-metadata", response_model=MetadataExtractionResult)
async def re_extract_document_metadata(
    document_id: uuid.UUID,
    use_llm: bool = Query(False),
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Re-analyze an existing document's file and return detected metadata (no save)."""
    document = await _get_document(db, document_id)
    try:
        path = document_service.safe_document_path(document)
    except DocumentValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    extension = f".{document.document_type}"
    parsed = await asyncio.to_thread(parse_document, str(path), extension)
    return await metadata_extractor.extract_metadata(
        db,
        filename=document.filename,
        parsed=parsed,
        file_path=str(path),
        extension=extension,
        use_llm=use_llm,
    )


@router.post("/{document_id}/reindex", response_model=DocumentOut)
async def reindex_document(
    document_id: uuid.UUID,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    document = await _get_document(db, document_id)
    if not document_service.safe_document_path(document).exists():
        raise HTTPException(status_code=400, detail="Original file missing on disk.")
    document.status = "UPLOADING"
    document.error_message = None
    await db.commit()
    start_indexing_task(document.id)
    await db.refresh(document)
    return _doc_out(document)


@router.delete("/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    _: Admin = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    document = await _get_document(db, document_id)
    from app.rag.vector_store import QdrantVectorStore

    await document_service.delete_document(db, document, QdrantVectorStore())
    return {"message": "Document deleted"}
