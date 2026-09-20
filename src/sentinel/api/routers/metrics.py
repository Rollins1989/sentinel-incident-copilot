from __future__ import annotations

from fastapi import APIRouter, Query

from sentinel.observability.metrics import metrics_summary


router = APIRouter()


@router.get("/metrics")
def metrics(limit: int = Query(default=50, ge=1, le=500)) -> dict:
    return metrics_summary(limit=limit)
