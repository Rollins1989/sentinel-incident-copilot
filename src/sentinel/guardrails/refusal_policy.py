"""Deterministic pre-generation refusal policy."""
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
    "I don't have enough information in the indexed runbooks, postmortems, or API docs "
    "to answer this confidently. Escalate to a human on-call engineer or add a runbook for this scenario."
)

DOMAIN_TERMS = {
    "api","service","server","database","db","pod","pods","kubernetes","deploy","deployment",
    "crashloopbackoff","incident","outage","error","errors","oomkilled","502","503","latency",
    "traffic","request","requests","retry","retries","backoff","webhook","payment","provider",
    "billing","checkout","notification","search","connection","connections","pool","authentication",
    "authenticate","token","api-key","rate","limit","remediation","diagnostic","root","cause",
    "postmortem","runbook","memory","restart","restarting",
}
OUT_OF_SCOPE_TERMS = {"pto","vacation","leave","holiday","salary","payroll","hiring","interview","performance","promotion","hr"}

def _words(question: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_-]+", question.lower()))

def evaluate_refusal(retrieved: list[RetrievedChunk], question: str | None = None) -> RefusalDecision:
    if not retrieved:
        return RefusalDecision(True, "no_chunks_retrieved", 0.0)
    top_score = retrieved[0].fused_score
    if top_score < settings.min_confidence:
        return RefusalDecision(True, "below_confidence_threshold", top_score)
    if question is not None:
        words = _words(question)
        if words & OUT_OF_SCOPE_TERMS or not words & DOMAIN_TERMS:
            return RefusalDecision(True, "out_of_scope", top_score)
    return RefusalDecision(False, None, top_score)
