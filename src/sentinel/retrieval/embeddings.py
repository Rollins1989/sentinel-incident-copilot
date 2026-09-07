"""
Embedding providers.

Two implementations behind one interface:

- SentenceTransformerEmbedder: real dense embeddings for production use.
  Downloads a small model on first run (requires network once).
- HashingEmbedder: a deterministic, dependency-free fallback used in tests,
  CI, and offline dev so the retrieval pipeline is fully exercisable without
  network access or a multi-hundred-MB model download. It is not semantically
  strong, but it is stable and lets every other layer (chunking, fusion,
  guardrails, API) be tested in isolation.

Swapping providers is a one-line config change (`EMBEDDING_PROVIDER`).
"""
from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from functools import lru_cache

import numpy as np

from sentinel.config import settings


class EmbeddingProvider(ABC):
    dim: int

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]


class HashingEmbedder(EmbeddingProvider):
    """Deterministic bag-of-tokens hashing embedder (offline, no model download)."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def _vector(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        for tok in tokens:
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h // self.dim) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t).tolist() for t in texts]


class SentenceTransformerEmbedder(EmbeddingProvider):
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # deferred import

        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()


@lru_cache(maxsize=1)
def get_embedder() -> EmbeddingProvider:
    if settings.embedding_provider == "sentence-transformer":
        return SentenceTransformerEmbedder(settings.embedding_model_name)
    return HashingEmbedder(dim=settings.embedding_dim)
