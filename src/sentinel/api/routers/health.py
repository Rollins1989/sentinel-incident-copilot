from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sentinel.config import settings
from sentinel.retrieval.bm25_index import BM25Index
from sentinel.retrieval.vector_store import VectorStore


router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "llm_provider": settings.llm_provider,
        "embedding_provider": settings.embedding_provider,
        "prompt_version": settings.prompt_version,
    }


@router.get("/ready")
def readiness() -> dict:
    vector_count = VectorStore().collection.count()
    bm25_ready = BM25Index().load()
    if vector_count == 0 or not bm25_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "not_ready",
                "vector_chunks": vector_count,
                "bm25_ready": bm25_ready,
            },
        )
    return {
        "status": "ready",
        "vector_chunks": vector_count,
        "bm25_ready": bm25_ready,
    }
