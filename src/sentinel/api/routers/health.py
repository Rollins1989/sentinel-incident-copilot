from __future__ import annotations

from fastapi import APIRouter

from sentinel.config import settings

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "embedding_provider": settings.embedding_provider,
        "prompt_version": settings.prompt_version,
    }
