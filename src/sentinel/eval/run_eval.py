"""
Eval harness.

This is the MLOps backbone of the project: prompt changes, retrieval
tuning, or model swaps are only ever accepted if they don't regress this
suite. It measures three independent things that a single "does it look
right" spot-check would conflate:

1. Retrieval quality  — did we retrieve a chunk from the *right* source
   document at all? (recall@k against golden_dataset.jsonl)
2. Groundedness        — does every citation the model emitted point at a
   chunk that was actually retrieved? (deterministic, see guardrails/)
3. Refusal correctness — does the system refuse exactly the out-of-scope
   questions, and answer exactly the in-scope ones?

Run with: `python -m sentinel.eval.run_eval`
Exits non-zero if any metric drops below its threshold, so it's usable as
a CI gate.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from sentinel.generation.answer_engine import AnswerEngine
from sentinel.observability.tracing import get_logger

log = get_logger("eval")

GOLDEN_PATH = Path(__file__).parent / "golden_dataset.jsonl"

# Minimum acceptable scores — tune these deliberately, not to make CI pass.
THRESHOLDS = {
    "retrieval_recall": 0.80,
    "refusal_accuracy": 0.90,
    "groundedness_rate": 0.90,
}


@dataclass
class CaseResult:
    id: str
    question: str
    category: str
    retrieval_hit: bool
    expected_refusal: bool
    actual_refusal: bool
    refusal_correct: bool
    grounded: bool
    confidence: float
    answer_preview: str


def _load_golden() -> list[dict]:
    cases = []
    with open(GOLDEN_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def run_eval() -> dict:
    cases = _load_golden()
    engine = AnswerEngine()
    results: list[CaseResult] = []

    for case in cases:
        result = engine.answer(case["question"])
        expected_stems = case.get("expected_doc_ids_contains", [])
        retrieved_paths = [c.metadata["source_path"] for c in result.retrieved_chunks]
        retrieval_hit = (
            any(any(stem in path for stem in expected_stems) for path in retrieved_paths)
            if expected_stems
            else True  # out-of-scope cases have no expected doc
        )
        expected_refusal = case.get("expect_refusal", False)
        refusal_correct = result.refused == expected_refusal

        results.append(
            CaseResult(
                id=case["id"],
                question=case["question"],
                category=case["category"],
                retrieval_hit=retrieval_hit,
                expected_refusal=expected_refusal,
                actual_refusal=result.refused,
                refusal_correct=refusal_correct,
                grounded=result.grounded,
                confidence=round(result.confidence, 4),
                answer_preview=result.answer[:160],
            )
        )

    n = len(results)
    retrieval_recall = sum(r.retrieval_hit for r in results) / n
    refusal_accuracy = sum(r.refusal_correct for r in results) / n
    groundedness_rate = sum(r.grounded for r in results) / n

    summary = {
        "n_cases": n,
        "retrieval_recall": round(retrieval_recall, 3),
        "refusal_accuracy": round(refusal_accuracy, 3),
        "groundedness_rate": round(groundedness_rate, 3),
        "thresholds": THRESHOLDS,
        "passed": (
            retrieval_recall >= THRESHOLDS["retrieval_recall"]
            and refusal_accuracy >= THRESHOLDS["refusal_accuracy"]
            and groundedness_rate >= THRESHOLDS["groundedness_rate"]
        ),
        "cases": [asdict(r) for r in results],
    }
    return summary


def print_report(summary: dict) -> None:
    print("=" * 70)
    print("SENTINEL EVAL REPORT")
    print("=" * 70)
    print(f"Cases run:           {summary['n_cases']}")
    print(f"Retrieval recall:    {summary['retrieval_recall']:.1%}  (threshold {THRESHOLDS['retrieval_recall']:.0%})")
    print(f"Refusal accuracy:    {summary['refusal_accuracy']:.1%}  (threshold {THRESHOLDS['refusal_accuracy']:.0%})")
    print(f"Groundedness rate:   {summary['groundedness_rate']:.1%}  (threshold {THRESHOLDS['groundedness_rate']:.0%})")
    print("-" * 70)
    for c in summary["cases"]:
        status = "PASS" if c["retrieval_hit"] and c["refusal_correct"] and c["grounded"] else "FAIL"
        print(f"[{status}] {c['id']:>4}  ({c['category']:<12}) conf={c['confidence']:.3f}  {c['question'][:60]}")
    print("=" * 70)
    print("RESULT:", "PASSED" if summary["passed"] else "FAILED")


if __name__ == "__main__":
    summary = run_eval()
    print_report(summary)
    Path("eval_report.json").write_text(json.dumps(summary, indent=2))
    sys.exit(0 if summary["passed"] else 1)
