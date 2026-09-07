from __future__ import annotations

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    prompt_version: str | None = None


class CitationOut(BaseModel):
    chunk_id: str
    title: str
    section: str
    source_path: str
    doc_type: str


class AskResponse(BaseModel):
    answer: str
    refused: bool
    refusal_reason: str | None
    grounded: bool
    invalid_citations: list[str]
    confidence: float
    citations: list[CitationOut]
    trace_id: str
    latency_ms: dict[str, float]


class FeedbackRequest(BaseModel):
    trace_id: str
    helpful: bool
    comment: str | None = None


class IngestResponse(BaseModel):
    n_docs: int
    n_chunks: int
    redaction_events: int
