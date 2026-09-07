"""
Refusal policy.

Applied BEFORE calling the LLM at all: if the top fused retrieval score is
below MIN_CONFIDENCE, the corpus almost certainly doesn't cover the
question, so we refuse deterministically instead of letting the model try
to answer from thin context and rationalize an unsupported remediation
step. This saves a generation call on the empty-corpus case and, more
importantly, removes the failure mode entirely rather than mitigating it
after the fact.
"""
from __future__ import annotations

from dataclasses import dataclass

from sentinel.config import settings
from sentinel.retrieval.hybrid_retriever import RetrievedChunk


@dataclass
class RefusalDecision:
    should_refuse: bool
    reason: str | None
    top_score: float


REFUSAL_MESSAGE = (
    "I don't have enough information in the indexed runbooks, postmortems, "
    "or API docs to answer this confidently. This may be a gap in the "
    "knowledge base — consider escalating to a human on-call engineer or "
    "adding a runbook for this scenario."
)


def evaluate_refusal(retrieved: list[RetrievedChunk]) -> RefusalDecision:
    if not retrieved:
        return RefusalDecision(should_refuse=True, reason="no_chunks_retrieved", top_score=0.0)
    top_score = retrieved[0].fused_score
    if top_score < settings.min_confidence:
        return RefusalDecision(
            should_refuse=True, reason="below_confidence_threshold", top_score=top_score
        )
    return RefusalDecision(should_refuse=False, reason=None, top_score=top_score)
