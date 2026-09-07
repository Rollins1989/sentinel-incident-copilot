"""
Dense vector store wrapper around ChromaDB.

Chosen over a hosted vector DB because Sentinel targets a single-team,
self-hosted deployment where "docker compose up" should be the entire
setup story — no external vector DB account or network dependency for
the retrieval-critical path.
"""
from __future__ import annotations

import chromadb

from sentinel.config import settings
from sentinel.ingestion.chunking import Chunk


class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection, metadata={"hnsw:space": "cosine"}
        )

    def reset(self) -> None:
        try:
            self.client.delete_collection(settings.chroma_collection)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=settings.chroma_collection, metadata={"hnsw:space": "cosine"}
        )

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if not chunks:
            return
        self.collection.add(
            ids=[c.chunk_id for c in chunks],
            embeddings=vectors,
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "doc_id": c.doc_id,
                    "doc_type": c.doc_type,
                    "title": c.title,
                    "section": c.section,
                    "source_path": c.source_path,
                }
                for c in chunks
            ],
        )

    def query(self, query_vector: list[float], top_k: int) -> list[dict]:
        if self.collection.count() == 0:
            return []
        res = self.collection.query(query_embeddings=[query_vector], n_results=min(top_k, self.collection.count()))
        out = []
        for i in range(len(res["ids"][0])):
            # Chroma cosine "distance" -> similarity
            distance = res["distances"][0][i]
            similarity = 1 - distance
            out.append(
                {
                    "chunk_id": res["ids"][0][i],
                    "text": res["documents"][0][i],
                    "metadata": res["metadatas"][0][i],
                    "score": similarity,
                }
            )
        return out
