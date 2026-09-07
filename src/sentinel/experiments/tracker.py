"""
Experiment tracker.

Every eval run is logged with the full config that produced it (chunk size,
top_k, RRF k, prompt version, embedding provider) alongside the resulting
metrics. This turns "we changed the chunk size and it felt better" into an
actual comparable record — the minimum viable version of what MLflow /
Weights & Biases give you, without adding an external dependency for a
project this size.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from sentinel.config import settings

RUNS_PATH = Path("experiment_runs.jsonl")


def log_run(eval_summary: dict, notes: str = "") -> dict:
    record = {
        "ts": time.time(),
        "notes": notes,
        "config": {
            "chunk_size_tokens": settings.chunk_size_tokens,
            "chunk_overlap_tokens": settings.chunk_overlap_tokens,
            "top_k_dense": settings.top_k_dense,
            "top_k_sparse": settings.top_k_sparse,
            "top_k_final": settings.top_k_final,
            "rrf_k": settings.rrf_k,
            "min_confidence": settings.min_confidence,
            "embedding_provider": settings.embedding_provider,
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
            "prompt_version": settings.prompt_version,
        },
        "metrics": {
            "retrieval_recall": eval_summary["retrieval_recall"],
            "refusal_accuracy": eval_summary["refusal_accuracy"],
            "groundedness_rate": eval_summary["groundedness_rate"],
            "passed": eval_summary["passed"],
        },
    }
    with open(RUNS_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")
    return record


def load_runs() -> list[dict]:
    if not RUNS_PATH.exists():
        return []
    with open(RUNS_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def compare_runs() -> None:
    runs = load_runs()
    if not runs:
        print("No experiment runs logged yet.")
        return
    print(f"{'ts':<12} {'chunk':<7} {'top_k':<6} {'recall':<8} {'refusal':<9} {'grounded':<9} {'passed'}")
    for r in runs[-20:]:
        c, m = r["config"], r["metrics"]
        print(
            f"{int(r['ts']):<12} {c['chunk_size_tokens']:<7} {c['top_k_final']:<6} "
            f"{m['retrieval_recall']:<8} {m['refusal_accuracy']:<9} {m['groundedness_rate']:<9} {m['passed']}"
        )


if __name__ == "__main__":
    compare_runs()
