from __future__ import annotations

from fastapi import APIRouter, HTTPException

from sentinel.api.schemas import AskRequest, AskResponse, CitationOut
from sentinel.generation.answer_engine import AnswerEngine

router = APIRouter()
_engine: AnswerEngine | None = None


def get_engine() -> AnswerEngine:
    global _engine
    if _engine is None:
        _engine = AnswerEngine()
    return _engine


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    try:
        result = get_engine().answer(req.question, prompt_version=req.prompt_version)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    return AskResponse(
        answer=result.answer,
        refused=result.refused,
        refusal_reason=result.refusal_reason,
        grounded=result.grounded,
        invalid_citations=result.invalid_citations,
        confidence=result.confidence,
        citations=[CitationOut(**vars(c)) for c in result.citations],
        trace_id=result.trace_id,
        latency_ms=result.latency_ms,
    )
