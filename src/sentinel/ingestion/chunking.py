"""
Chunking.

Naive fixed-window chunking on runbooks is a common source of RAG failure:
it slices a numbered remediation step away from its precondition, so the
model retrieves "Step 4: restart the pod" without the "only if CPU > 90%"
guard from Step 3. Sentinel chunks along markdown structure first (headings,
then paragraphs/list items) and only falls back to a token-window split for
oversized sections, keeping remediation steps intact wherever the source
formatting allows it.

Token counting is approximated with a whitespace heuristic (~4 chars/token)
to avoid a hard dependency on a tokenizer library for this step; retrieval
correctness only needs consistent, not exact, chunk sizing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from sentinel.ingestion.loaders import RawDocument

CHARS_PER_TOKEN = 4


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    doc_type: str
    title: str
    section: str
    text: str
    source_path: str
    chunk_index: int


def _split_by_heading(text: str) -> list[tuple[str, str]]:
    """Split markdown into (heading, body) sections. Preamble gets heading ''."""
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_heading = ""
    current_body: list[str] = []
    for line in lines:
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            if current_body or current_heading:
                sections.append((current_heading, current_body))
            current_heading = m.group(2).strip()
            current_body = []
        else:
            current_body.append(line)
    sections.append((current_heading, current_body))
    return [(h, "\n".join(b).strip()) for h, b in sections if "\n".join(b).strip() or h]


def _token_len(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _window_split(text: str, size: int, overlap: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    step = max(1, size - overlap)
    chunks = []
    i = 0
    while i < len(words):
        window = words[i : i + size]
        chunks.append(" ".join(window))
        if i + size >= len(words):
            break
        i += step
    return chunks


def chunk_document(doc: RawDocument, chunk_size_tokens: int = 300, overlap_tokens: int = 60) -> list[Chunk]:
    sections = _split_by_heading(doc.text)
    chunks: list[Chunk] = []
    idx = 0
    for heading, body in sections:
        if not body:
            continue
        if _token_len(body) <= chunk_size_tokens:
            pieces = [body]
        else:
            pieces = _window_split(body, chunk_size_tokens, overlap_tokens)
        for piece in pieces:
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}::{idx}",
                    doc_id=doc.doc_id,
                    doc_type=doc.doc_type,
                    title=doc.title,
                    section=heading or doc.title,
                    text=piece,
                    source_path=doc.source_path,
                    chunk_index=idx,
                )
            )
            idx += 1
    return chunks
