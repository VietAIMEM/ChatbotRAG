from __future__ import annotations

import mimetypes
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.document_processing.parser import EXTENSIBLE_EXTENSIONS, EXTENSION_TYPE, SUPPORTED_EXTENSIONS
from app.models.conversation import MessageSource
from app.models.document import Document, DocumentChunk
from app.schemas.document import DocumentOut
from app.rag.vector_store import QdrantVectorStore

logger = get_logger(__name__)


class DocumentValidationError(Exception):
    pass


def get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def validate_upload(filename: str, size: int, max_size_mb: int) -> tuple[str, str]:
    ext = get_extension(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        hint = ""
        if ext in EXTENSIBLE_EXTENSIONS:
            hint = " Support for this format is planned but not yet available."
        raise DocumentValidationError(
            f"Unsupported file type '{ext or 'unknown'}'. Supported: .pdf, .doc, .docx, .txt, .md.{hint}"
        )
    if size > max_size_mb * 1024 * 1024:
        raise DocumentValidationError(
            f"File too large. Maximum allowed size is {max_size_mb} MB."
        )
    return ext, EXTENSION_TYPE[ext]


def safe_storage_name(upload_filename: str, ext: str) -> str:
    return f"{uuid.uuid4().hex}{ext}"


def storage_dir() -> Path:
    path = Path(settings.DOCUMENT_STORAGE_PATH)
    path.mkdir(parents=True, exist_ok=True)
    return path


async def store_uploaded_file(
    db: AsyncSession,
    upload: UploadFile,
    *,
    metadata: dict | None = None,
    max_size_mb: int | None = None,
) -> tuple[Document, str]:
    max_size = max_size_mb or settings.MAX_UPLOAD_SIZE_MB
    ext, document_type = validate_upload(upload.filename or "", 0, max_size)

    content = await upload.read()
    if not content:
        raise DocumentValidationError("Uploaded file is empty.")
    if len(content) > max_size * 1024 * 1024:
        raise DocumentValidationError(f"File too large. Maximum allowed size is {max_size} MB.")

    stored_name = safe_storage_name(upload.filename or "upload", ext)
    target = storage_dir() / stored_name
    target.write_bytes(content)

    metadata = metadata or {}
    title = metadata.get("title") or Path(upload.filename or "document").stem
    document = Document(
        filename=upload.filename or stored_name,
        stored_name=stored_name,
        title=title,
        description=metadata.get("description"),
        category=metadata.get("category"),
        year=metadata.get("year"),
        version=metadata.get("version"),
        document_type=document_type,
        file_size=len(content),
        file_path=str(target),
        status="UPLOADING",
        department=metadata.get("department"),
        program=metadata.get("program"),
        language=metadata.get("language") or "vi",
        effective_date=metadata.get("effective_date"),
        expiration_date=metadata.get("expiration_date"),
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)
    return document, str(target)


def build_document_out(document: Document) -> DocumentOut:
    out = DocumentOut.model_validate(document)
    out.download_url = f"/api/documents/{document.id}/download"
    out.view_url = f"/api/documents/{document.id}/view"
    return out


async def update_document(db: AsyncSession, document: Document, values: dict) -> Document:
    allowed = {
        "title", "description", "category", "year", "version",
        "department", "program", "language", "effective_date", "expiration_date", "is_active",
    }
    for key, value in values.items():
        if key in allowed:
            setattr(document, key, value)
    await db.commit()
    await db.refresh(document)
    return document


async def delete_document(db: AsyncSession, document: Document, vector_store: QdrantVectorStore) -> None:
    try:
        await vector_store.delete_by_document(str(document.id))
    except Exception as exc:
        logger.warning("vector delete failed during document deletion id=%s error=%s", document.id, exc)
    file_path = Path(document.file_path)
    if file_path.exists():
        file_path.unlink(missing_ok=True)
    await db.execute(sa_delete(MessageSource).where(MessageSource.document_id == document.id))
    await db.execute(sa_delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
    await db.delete(document)
    await db.commit()


def safe_document_path(document: Document) -> Path:
    base = storage_dir().resolve()
    candidate = Path(document.file_path).resolve()
    if not candidate.is_relative_to(base):
        raise DocumentValidationError("Invalid document path.")
    if not candidate.exists():
        raise DocumentValidationError("Document file not found on disk.")
    return candidate


def guess_content_type(document: Document) -> str:
    return mimetypes.guess_type(document.filename)[0] or "application/octet-stream"
