"""
Lightweight metrics store.

Records one row per query: latency breakdown, retrieved chunk ids, confidence
score, guardrail decision, token counts, and estimated cost. Backed by SQLite
so it works with zero extra infrastructure; swap for a Prometheus pushgateway
or a warehouse sink in a real deployment without touching call sites.
"""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from sentinel.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS query_events (
    trace_id TEXT PRIMARY KEY,
    ts REAL,
    question TEXT,
    prompt_version TEXT,
    retrieval_ms REAL,
    generation_ms REAL,
    total_ms REAL,
    confidence REAL,
    refused INTEGER,
    n_chunks_retrieved INTEGER,
    retrieved_chunk_ids TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    estimated_cost_usd REAL
);
"""


@contextmanager
def _conn():
    Path(settings.experiments_db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.experiments_db)
    try:
        conn.execute(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def record_query_event(**fields) -> None:
    fields.setdefault("ts", time.time())
    if "retrieved_chunk_ids" in fields and isinstance(fields["retrieved_chunk_ids"], list):
        fields["retrieved_chunk_ids"] = json.dumps(fields["retrieved_chunk_ids"])
    with _conn() as conn:
        cols = ", ".join(fields.keys())
        placeholders = ", ".join("?" for _ in fields)
        conn.execute(
            f"INSERT OR REPLACE INTO query_events ({cols}) VALUES ({placeholders})",
            list(fields.values()),
        )


def recent_events(limit: int = 50) -> list[dict]:
    with _conn() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM query_events ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# Rough per-1M-token pricing used only for local cost visibility (not billing-accurate).
_PRICE_PER_M_INPUT = 3.00
_PRICE_PER_M_OUTPUT = 15.00


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    return round(
        (input_tokens / 1_000_000) * _PRICE_PER_M_INPUT
        + (output_tokens / 1_000_000) * _PRICE_PER_M_OUTPUT,
        6,
    )
