from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Postgraduate Information Assistant"
    API_V1_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Security
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    ADMIN_COOKIE_NAME: str = "admin_token"

    # Database
    DATABASE_URL: str

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL

        if url.startswith("postgres://"):
            return url.replace(
                "postgres://",
                "postgresql+asyncpg://",
                1,
            )

        if url.startswith("postgresql://"):
            return url.replace(
                "postgresql://",
                "postgresql+asyncpg://",
                1,
            )

        return url

    # Qdrant
    QDRANT_URL: str
    QDRANT_COLLECTION: str = "postgraduate_documents"
    QDRANT_VECTOR_SIZE: int = 768

    # Storage
    DOCUMENT_STORAGE_PATH: str = "./storage/documents"
    MAX_UPLOAD_SIZE_MB: int = 20

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True

    # Public defaults
    DEFAULT_EMBEDDING_PROVIDER: str = "local"
    DEFAULT_EMBEDDING_MODEL: str = "hash-bge-m3-v1"
    DEFAULT_RERANKER_PROVIDER: str = "local"
    DEFAULT_RERANKER_MODEL: str = "lexical"
    DEFAULT_CHUNK_SIZE: int = 800
    DEFAULT_CHUNK_OVERLAP: int = 150
    DEFAULT_TOP_K: int = 10
    DEFAULT_FINAL_K: int = 5
    DEFAULT_SIMILARITY_THRESHOLD: float = 0.35
    DEFAULT_ENABLE_RERANKER: bool = True
    DEFAULT_ENABLE_QUERY_REWRITE: bool = True

    # Chat
    CHAT_RATE_LIMIT_PER_MINUTE: int = 30
    CHAT_RATE_LIMIT_WINDOW_SECONDS: int = 60
    ADMIN_LOGIN_RATE_LIMIT_PER_MINUTE: int = 10
    CONVERSATION_MEMORY_MESSAGES: int = 8

    # LLM
    OPENROUTER_API_KEY: str = ""
    LLM_DEFAULT_TEMPERATURE: float = 0.2
    LLM_DEFAULT_MAX_TOKENS: int = 1024
    LLM_DEFAULT_TIMEOUT: int = 120

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [
                    item.strip()
                    for item in v.split(",")
                    if item.strip()
                ]
        return v

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
