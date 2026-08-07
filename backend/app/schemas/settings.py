from __future__ import annotations

from pydantic import BaseModel, Field


class PublicSettingsOut(BaseModel):
    site_name: str
    chatbot_name: str
    welcome_message: str


class GeneralSettingsUpdate(BaseModel):
    site_name: str = "Postgraduate Information Assistant"
    chatbot_name: str = "Postgraduate Information Assistant"
    welcome_message: str = ""


class SecuritySettingsUpdate(BaseModel):
    chat_rate_limit_per_minute: int = Field(default=30, ge=1, le=1000)
    max_upload_size_mb: int = Field(default=20, ge=1, le=200)


class MetadataCategorySettings(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    keywords: list[str] = Field(default_factory=list)


class MetadataSettingsUpdate(BaseModel):
    categories: list[MetadataCategorySettings] = Field(default_factory=list)
    departments: list[str] = Field(default_factory=list)
    programs: list[str] = Field(default_factory=list)


class SettingsUpdate(BaseModel):
    general: GeneralSettingsUpdate | None = None
    security: SecuritySettingsUpdate | None = None
    metadata: MetadataSettingsUpdate | None = None


class SettingsOut(BaseModel):
    general: GeneralSettingsUpdate
    security: SecuritySettingsUpdate
    metadata: MetadataSettingsUpdate = Field(default_factory=MetadataSettingsUpdate)
