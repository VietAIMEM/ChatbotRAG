from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class RAGConfigUpdate(BaseModel):
    embedding_provider: str = "local"
    embedding_model: str = "hash-bge-m3-v1"
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    reranker_provider: str = "local"
    reranker_model: str = "lexical"
    chunk_size: int = Field(default=800, ge=100, le=4096)
    chunk_overlap: int = Field(default=150, ge=0, le=1024)
    top_k: int = Field(default=10, ge=1, le=50)
    final_k: int = Field(default=5, ge=1, le=20)
    similarity_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    enable_query_rewrite: bool = True
    enable_reranker: bool = True

    @model_validator(mode="after")
    def _validate(self) -> "RAGConfigUpdate":
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if self.final_k > self.top_k:
            raise ValueError("final_k must be <= top_k")
        return self


class RAGConfigOut(RAGConfigUpdate):
    pass


class AvailableModel(BaseModel):
    value: str
    label: str
