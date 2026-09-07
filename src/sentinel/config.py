"""
Central configuration for Sentinel.

All tunables live here and are overridable via environment variables / .env,
so the same codebase runs identically in dev, CI, and prod with no code edits.
"""
from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- LLM ---
    anthropic_api_key: str | None = None
    llm_provider: str = "mock"  # "anthropic" | "mock"
    llm_model: str = "claude-sonnet-4-5"
    llm_judge_model: str = "claude-sonnet-4-5"

    # --- Embeddings ---
    embedding_provider: str = "hashing"  # "sentence-transformer" | "hashing"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # --- Vector store ---
    chroma_persist_dir: str = ".chroma"
    chroma_collection: str = "sentinel_chunks"

    # --- Retrieval ---
    top_k_dense: int = 8
    top_k_sparse: int = 8
    top_k_final: int = 5
    rrf_k: int = 10

    # --- Guardrails ---
    # RRF score floor before we allow generation. With rrf_k=10, a chunk ranked
    # #1 by both dense and sparse retrieval scores ~2/(10+1) = 0.18; a chunk
    # that shows up only weakly in one ranker scores well under 0.05. This
    # threshold is tuned against the eval harness, not guessed — see
    # eval/run_eval.py and README "Tuning the confidence threshold".
    min_confidence: float = 0.05
    max_answer_tokens: int = 1024

    # --- Chunking ---
    chunk_size_tokens: int = 300
    chunk_overlap_tokens: int = 60

    # --- Prompting / MLOps ---
    prompt_version: str = "v1"

    # --- Paths ---
    data_dir: Path = Path("data")
    experiments_db: Path = Path("experiments.db")
    logs_dir: Path = Path("logs")


settings = Settings()
