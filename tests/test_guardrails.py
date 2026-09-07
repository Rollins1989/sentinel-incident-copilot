import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.guardrails.groundedness import check_groundedness
from sentinel.guardrails.refusal_policy import evaluate_refusal
from sentinel.retrieval.hybrid_retriever import RetrievedChunk


def _rc(chunk_id, score):
    return RetrievedChunk(chunk_id=chunk_id, text="t", metadata={}, fused_score=score, dense_rank=0, sparse_rank=0)


def test_groundedness_flags_invalid_citation():
    answer = "Restart the pod [doc-a::0] then check logs [doc-x::9]."
    result = check_groundedness(answer, retrieved_chunk_ids=["doc-a::0", "doc-a::1"])
    assert not result.is_grounded
    assert "doc-x::9" in result.invalid_citations


def test_groundedness_passes_when_all_citations_valid():
    answer = "Restart the pod [doc-a::0]."
    result = check_groundedness(answer, retrieved_chunk_ids=["doc-a::0"])
    assert result.is_grounded


def test_refusal_triggered_below_confidence():
    decision = evaluate_refusal([_rc("c1", 0.01)])
    assert decision.should_refuse


def test_refusal_triggered_on_empty_retrieval():
    decision = evaluate_refusal([])
    assert decision.should_refuse
    assert decision.reason == "no_chunks_retrieved"


def test_no_refusal_above_confidence():
    decision = evaluate_refusal([_rc("c1", 0.5)])
    assert not decision.should_refuse
