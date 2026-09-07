"""
Ingestion pipeline: load -> redact -> chunk -> embed -> index (dense + sparse).

Idempotent by design: doc_ids are content hashes, chunk_ids are derived
from doc_id, so re-running ingest on an unchanged corpus is a safe no-op
and changed files simply overwrite their old chunks.
"""
from __future__ import annotations

from pathlib import Path

from sentinel.config import settings
from sentinel.ingestion.chunking import Chunk, chunk_document
from sentinel.ingestion.loaders import load_all_sources
from sentinel.ingestion.redact import redact
from sentinel.observability.tracing import get_logger
from sentinel.retrieval.bm25_index import BM25Index
from sentinel.retrieval.embeddings import get_embedder
from sentinel.retrieval.vector_store import VectorStore

log = get_logger("ingestion")


def run_ingestion(data_dir: Path | None = None) -> dict:
    data_dir = data_dir or settings.data_dir
    raw_docs = load_all_sources(data_dir)
    log.info("ingestion.loaded", extra={"n_docs": len(raw_docs)})

    all_chunks: list[Chunk] = []
    redaction_events = 0
    for doc in raw_docs:
        clean_text, findings = redact(doc.text)
        if findings:
            redaction_events += len(findings)
            log.warning("ingestion.redacted", extra={"doc_id": doc.doc_id, "findings": findings})
        doc.text = clean_text
        all_chunks.extend(
            chunk_document(doc, settings.chunk_size_tokens, settings.chunk_overlap_tokens)
        )

    embedder = get_embedder()
    vectors = embedder.embed([c.text for c in all_chunks]) if all_chunks else []

    store = VectorStore()
    store.reset()
    store.add(all_chunks, vectors)

    bm25 = BM25Index()
    bm25.build(all_chunks)
    bm25.save()

    log.info(
        "ingestion.complete",
        extra={"n_chunks": len(all_chunks), "n_docs": len(raw_docs), "redaction_events": redaction_events},
    )
    return {
        "n_docs": len(raw_docs),
        "n_chunks": len(all_chunks),
        "redaction_events": redaction_events,
    }


if __name__ == "__main__":
    result = run_ingestion()
    print(result)
