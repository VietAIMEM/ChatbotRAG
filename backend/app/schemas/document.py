from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentMetadata(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    year: int | None = None
    version: str | None = None
    department: str | None = None
    program: str | None = None
    language: str | None = "vi"
    effective_date: date | None = None
    expiration_date: date | None = None


class DocumentCreate(DocumentMetadata):
    pass


class DocumentUpdate(DocumentMetadata):
    is_active: bool | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    title: str
    description: str | None = None
    category: str | None = None
    year: int | None = None
    version: str | None = None
    document_type: str
    file_size: int
    status: str
    error_message: str | None = None
    is_active: bool
    department: str | None = None
    program: str | None = None
    language: str | None = None
    effective_date: date | None = None
    expiration_date: date | None = None
    chunk_count: int
    created_at: datetime
    updated_at: datetime

    download_url: str | None = None
    view_url: str | None = None


class DocumentListResponse(BaseModel):
    items: list[DocumentOut]
    total: int


class UploadResult(BaseModel):
    document: DocumentOut
    message: str


class MetadataField(BaseModel):
    value: str | int | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    method: str = "none"


class MetadataExtractionResult(BaseModel):
    filename: str
    title: MetadataField
    category: MetadataField
    year: MetadataField
    version: MetadataField
    department: MetadataField
    program: MetadataField
    language: MetadataField
    description: MetadataField
