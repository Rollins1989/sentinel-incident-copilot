"""
Hybrid retrieval via Reciprocal Rank Fusion (RRF).

RRF combines two ranked lists (dense, sparse) using only rank position, not
raw scores — which sidesteps the classic problem that cosine similarity and
BM25 scores live on incomparable scales and can't be linearly blended
without careful (and fragile) tuning. RRF is the same fusion strategy used
in most production hybrid-search systems (e.g. Elastic, Vespa) for exactly
this reason.

score(d) = sum over rankers r of  1 / (k + rank_r(d))
"""
from __future__ import annotations

from dataclasses import dataclass

from sentinel.config import settings
from sentinel.retrieval.bm25_index import BM25Index
from sentinel.retrieval.embeddings import get_embedder
from sentinel.retrieval.vector_store import VectorStore


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    metadata: dict
    fused_score: float
    dense_rank: int | None
    sparse_rank: int | None


class HybridRetriever:
    def __init__(self):
        self.embedder = get_embedder()
        self.vector_store = VectorStore()
        self.bm25 = BM25Index()
        if not self.bm25.load():
            self.bm25.build([])  # empty index until ingestion runs

    def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        top_k = top_k or settings.top_k_final
        query_vec = self.embedder.embed_query(query)

        dense_hits = self.vector_store.query(query_vec, settings.top_k_dense)
        sparse_hits = self.bm25.query(query, settings.top_k_sparse)

        dense_rank = {h["chunk_id"]: i for i, h in enumerate(dense_hits)}
        sparse_rank = {h["chunk_id"]: i for i, h in enumerate(sparse_hits)}

        by_id: dict[str, dict] = {}
        for h in dense_hits + sparse_hits:
            by_id.setdefault(h["chunk_id"], h)

        k = settings.rrf_k
        fused: list[RetrievedChunk] = []
        for chunk_id, hit in by_id.items():
            d_rank = dense_rank.get(chunk_id)
            s_rank = sparse_rank.get(chunk_id)
            score = 0.0
            if d_rank is not None:
                score += 1.0 / (k + d_rank + 1)
            if s_rank is not None:
                score += 1.0 / (k + s_rank + 1)
            fused.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    text=hit["text"],
                    metadata=hit["metadata"],
                    fused_score=score,
                    dense_rank=d_rank,
                    sparse_rank=s_rank,
                )
            )

        fused.sort(key=lambda c: c.fused_score, reverse=True)
        return fused[:top_k]
