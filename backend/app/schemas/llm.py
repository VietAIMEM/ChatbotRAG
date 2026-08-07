from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.llm import PROVIDER_TYPES


class LLMProviderBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    provider_type: str = Field(default="openai_compatible")
    base_url: str = ""
    model: str = ""
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=128000)
    timeout: int = Field(default=120, ge=1, le=600)
    enabled: bool = True
    priority: int = Field(default=100, ge=0, le=1000)
    extra: dict[str, Any] = {}

    @model_validator(mode="after")
    def _validate_provider_type(self) -> "LLMProviderBase":
        if self.provider_type not in PROVIDER_TYPES:
            raise ValueError(f"provider_type must be one of {PROVIDER_TYPES}")
        return self


class LLMProviderCreate(LLMProviderBase):
    api_key: str | None = None


class LLMProviderUpdate(BaseModel):
    name: str | None = None
    provider_type: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    timeout: int | None = None
    enabled: bool | None = None
    priority: int | None = None
    extra: dict[str, Any] | None = None


class LLMProviderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    provider_type: str
    base_url: str
    model: str
    temperature: float
    max_tokens: int
    timeout: int
    enabled: bool
    priority: int
    has_api_key: bool = False
    api_key_masked: str = ""
    extra: dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime


class TestProviderResult(BaseModel):
    success: bool
    message: str
    provider: str | None = None
    model: str | None = None
