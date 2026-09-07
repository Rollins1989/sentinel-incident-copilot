from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import APIRouter

from sentinel.api.schemas import FeedbackRequest
from sentinel.config import settings

router = APIRouter()


@router.post("/feedback")
def submit_feedback(req: FeedbackRequest) -> dict:
    """
    Human feedback on a specific trace_id. This is the raw signal that a
    real deployment would use to build a growing eval regression set:
    thumbs-down traces are exactly the cases worth adding to
    eval/golden_dataset.jsonl after triage.
    """
    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    path = settings.logs_dir / "feedback.jsonl"
    with open(path, "a") as f:
        f.write(json.dumps({**req.model_dump(), "ts": time.time()}) + "\n")
    return {"status": "recorded"}
