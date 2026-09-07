import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.ingestion.chunking import chunk_document
from sentinel.ingestion.loaders import RawDocument


def make_doc(text: str) -> RawDocument:
    return RawDocument(doc_id="d1", source_path="x.md", doc_type="runbook", title="Test Doc", text=text)


def test_heading_split_keeps_sections_separate():
    text = "# Title\n\n## Symptoms\nSomething is broken.\n\n## Remediation\nRestart it.\n"
    doc = make_doc(text)
    chunks = chunk_document(doc, chunk_size_tokens=300, overlap_tokens=60)
    sections = {c.section for c in chunks}
    assert "Symptoms" in sections
    assert "Remediation" in sections


def test_large_section_gets_windowed():
    body = " ".join([f"word{i}" for i in range(2000)])
    text = f"# Title\n\n## Big Section\n{body}\n"
    doc = make_doc(text)
    chunks = chunk_document(doc, chunk_size_tokens=100, overlap_tokens=20)
    assert len(chunks) > 1
    # consecutive chunks should overlap by ~overlap_tokens words
    first_tail = chunks[0].text.split()[-20:]
    second_head = chunks[1].text.split()[:20]
    assert set(first_tail) & set(second_head)


def test_chunk_ids_are_unique_and_stable_per_doc():
    text = "# T\n\n## A\nfoo\n\n## B\nbar\n"
    doc = make_doc(text)
    chunks = chunk_document(doc)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    assert all(c.doc_id == "d1" for c in chunks)
