from __future__ import annotations

from fastapi import APIRouter

from sentinel.api.schemas import IngestResponse
from sentinel.api.security import AdminGuard
from sentinel.ingestion.pipeline import run_ingestion


router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
def ingest(_: AdminGuard) -> IngestResponse:
    return IngestResponse(**run_ingestion())
