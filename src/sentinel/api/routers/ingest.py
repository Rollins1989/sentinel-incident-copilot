from __future__ import annotations

from fastapi import APIRouter

from sentinel.api.schemas import IngestResponse
from sentinel.ingestion.pipeline import run_ingestion

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
def ingest() -> IngestResponse:
    """
    Re-run the ingestion pipeline over the configured data directory.
    Idempotent: content-hashed doc_ids mean re-ingesting unchanged files
    is a safe no-op. Triggers a fresh HybridRetriever on next /ask call
    by simply re-reading the persisted stores.
    """
    result = run_ingestion()
    return IngestResponse(**result)
