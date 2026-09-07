"""
BM25 sparse lexical index.

Dense embeddings alone miss exact-match signal that matters a lot for ops
docs: error codes ("ECONNREFUSED"), env var names, service names, HTTP
status codes. BM25 catches these verbatim; fusing it with dense retrieval
(see hybrid_retriever.py) covers both "what does this mean semantically"
and "find the doc that literally contains this token" queries.
"""
from __future__ import annotations

import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from sentinel.config import settings
from sentinel.ingestion.chunking import Chunk


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


class BM25Index:
    def __init__(self):
        self.bm25: BM25Okapi | None = None
        self.chunks: list[Chunk] = []

    @property
    def _path(self) -> Path:
        return Path(settings.chroma_persist_dir) / "bm25_index.pkl"

    def build(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        tokenized = [_tokenize(c.text) for c in chunks]
        self.bm25 = BM25Okapi(tokenized) if tokenized else None

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._path, "wb") as f:
            pickle.dump({"chunks": self.chunks}, f)
        # Rebuild-on-load is cheap and avoids pickling the BM25Okapi internals.

    def load(self) -> bool:
        if not self._path.exists():
            return False
        with open(self._path, "rb") as f:
            data = pickle.load(f)
        self.build(data["chunks"])
        return True

    def query(self, query_text: str, top_k: int) -> list[dict]:
        if self.bm25 is None or not self.chunks:
            return []
        scores = self.bm25.get_scores(_tokenize(query_text))
        ranked = sorted(zip(self.chunks, scores), key=lambda x: x[1], reverse=True)[:top_k]
        return [
            {
                "chunk_id": c.chunk_id,
                "text": c.text,
                "metadata": {
                    "doc_id": c.doc_id,
                    "doc_type": c.doc_type,
                    "title": c.title,
                    "section": c.section,
                    "source_path": c.source_path,
                },
                "score": float(score),
            }
            for c, score in ranked
            if score > 0
        ]
