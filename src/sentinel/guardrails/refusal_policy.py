"""
Deterministic refusal policy for out-of-scope questions.
"""

from __future__ import annotations

import re
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


# Words that strongly indicate Sentinel's incident-response domain.
DOMAIN_TERMS = {
    "api",
    "service",
    "server",
    "database",
    "db",
    "pod",
    "pods",
    "kubernetes",
    "deploy",
    "deployment",
    "crashloopbackoff",
    "incident",
    "outage",
    "error",
    "errors",
    "502",
    "503",
    "latency",
    "traffic",
    "request",
    "requests",
    "retry",
    "retries",
    "backoff",
    "webhook",
    "payment",
    "provider",
    "billing",
    "checkout",
    "notification",
    "search",
    "connection",
    "connections",
    "pool",
    "authentication",
    "authenticate",
    "token",
    "api-key",
    "rate",
    "limit",
    "remediation",
    "diagnostic",
    "root",
    "cause",
    "postmortem",
    "runbook",
}


def _has_domain_signal(question: str) -> bool:
    """Return True when the question contains a meaningful technical signal."""
    words = set(re.findall(r"[a-z0-9_-]+", question.lower()))
    return bool(words & DOMAIN_TERMS)

OUT_OF_SCOPE_TERMS = {
    "pto",
    "vacation",
    "leave",
    "holiday",
    "salary",
    "payroll",
    "hiring",
    "interview",
    "performance",
    "promotion",
    "hr",
}


def _is_obviously_out_of_scope(question: str) -> bool:
    """Reject requests that clearly belong to unrelated business domains."""
    words = set(re.findall(r"[a-z0-9_-]+", question.lower()))
    return bool(words & OUT_OF_SCOPE_TERMS)

def evaluate_refusal(
    retrieved: list[RetrievedChunk],
    question: str | None = None,
) -> RefusalDecision:
    if not retrieved:
        return RefusalDecision(
            should_refuse=True,
            reason="no_chunks_retrieved",
            top_score=0.0,
        )

    top_score = retrieved[0].fused_score

    if top_score < settings.min_confidence:
        return RefusalDecision(
            should_refuse=True,
            reason="below_confidence_threshold",
            top_score=top_score,
        )

    # If we know the question, reject questions that have no
    # meaningful Sentinel/incident-response domain signal.
    if question is not None and (
        _is_obviously_out_of_scope(question)
        or not _has_domain_signal(question)
    ):
        return RefusalDecision(
            should_refuse=True,
            reason="out_of_scope",
            top_score=top_score,
        )

    # Weak evidence from only one retrieval method is not sufficient.
    top = retrieved[0]
    appears_in_both = (
        top.dense_rank is not None
        and top.sparse_rank is not None
    )

    if not appears_in_both and top_score < 0.18:
        return RefusalDecision(
            should_refuse=True,
            reason="insufficient_relevance_evidence",
            top_score=top_score,
        )

    return RefusalDecision(
        should_refuse=False,
        reason=None,
        top_score=top_score,
    )