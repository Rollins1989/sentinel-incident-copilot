"""Central, environment-driven configuration for Sentinel."""
from __future__ import annotations

from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False)
    app_name: str = "Sentinel"
    app_version: str = "0.2.0"
    environment: str = "development"
    log_level: str = "INFO"
    anthropic_api_key: str | None = None
    llm_provider: str = "mock"
    llm_model: str = "claude-sonnet-4-5"
    llm_judge_model: str = "claude-sonnet-4-5"
    embedding_provider: str = "hashing"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384
    chroma_persist_dir: str = ".chroma"
    chroma_collection: str = "sentinel_chunks"
    top_k_dense: int = Field(default=8, ge=1, le=50)
    top_k_sparse: int = Field(default=8, ge=1, le=50)
    top_k_final: int = Field(default=5, ge=1, le=20)
    rrf_k: int = Field(default=10, ge=1, le=100)
    min_confidence: float = Field(default=0.05, ge=0.0, le=1.0)
    max_answer_tokens: int = Field(default=1024, ge=64, le=8192)
    chunk_size_tokens: int = Field(default=300, ge=50, le=2000)
    chunk_overlap_tokens: int = Field(default=60, ge=0, le=500)
    prompt_version: str = "v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8000", "http://127.0.0.1:8000"])
    allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1", "testserver"])
    admin_token: str | None = None
    data_dir: Path = Path("data")
    experiments_db: Path = Path("experiments.db")
    logs_dir: Path = Path("logs")

    @field_validator("cors_origins", "allowed_hosts", mode="before")
    @classmethod
    def parse_csv(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

settings = Settings()
