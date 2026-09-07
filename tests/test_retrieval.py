import os
import sys
from pathlib import Path

os.environ["EMBEDDING_PROVIDER"] = "hashing"
os.environ["CHROMA_PERSIST_DIR"] = ".chroma_test"

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.ingestion.chunking import chunk_document
from sentinel.ingestion.loaders import RawDocument
from sentinel.retrieval.bm25_index import BM25Index
from sentinel.retrieval.embeddings import get_embedder
from sentinel.retrieval.vector_store import VectorStore


def _build_test_corpus():
    # BM25's classic IDF term is ~0 for words appearing in exactly half of a
    # 2-document corpus, so we use enough documents for IDF to be meaningful.
    docs = [
        RawDocument("doc-a", "a.md", "runbook", "Pod CrashLoop", "# Pod CrashLoop\n\n## Fix\nCheck memory limits and restart the pod after fixing OOM.", {}),
        RawDocument("doc-b", "b.md", "runbook", "DB Pool", "# DB Pool\n\n## Fix\nIncrease connection pool size and check for leaks.", {}),
        RawDocument("doc-c", "c.md", "runbook", "Disk Space", "# Disk Space\n\n## Fix\nClear old log files to free disk space on the node.", {}),
        RawDocument("doc-d", "d.md", "runbook", "Slow Queries", "# Slow Queries\n\n## Fix\nAdd an index to speed up the slow query path.", {}),
    ]
    chunks = []
    for d in docs:
        chunks.extend(chunk_document(d))
    return chunks


def test_bm25_finds_lexical_match():
    chunks = _build_test_corpus()
    idx = BM25Index()
    idx.build(chunks)
    results = idx.query("connection pool leaks", top_k=3)
    assert results
    assert any("pool" in r["text"].lower() for r in results)


def test_vector_store_roundtrip():
    chunks = _build_test_corpus()
    embedder = get_embedder()
    vectors = embedder.embed([c.text for c in chunks])
    store = VectorStore()
    store.reset()
    store.add(chunks, vectors)
    query_vec = embedder.embed_query("memory limits OOM pod")
    results = store.query(query_vec, top_k=2)
    assert results
    assert results[0]["score"] <= 1.0001
