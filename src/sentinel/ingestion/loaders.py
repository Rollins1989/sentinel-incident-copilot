"""
Document loaders.

Sentinel ingests three source types that make up an engineering org's tribal
knowledge: runbooks, postmortems, and API docs. Each loader normalizes the
source into a `RawDocument` with consistent metadata so downstream chunking
and retrieval don't need to special-case file types.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RawDocument:
    doc_id: str
    source_path: str
    doc_type: str  # "runbook" | "postmortem" | "api_doc"
    title: str
    text: str
    metadata: dict = field(default_factory=dict)


def _doc_id_for(path: Path) -> str:
    """Stable content-addressed ID so re-ingesting unchanged files is a no-op."""
    h = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    return f"{path.stem}-{h}"


def _extract_title(text: str, fallback: str) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else fallback


def load_markdown_dir(directory: Path, doc_type: str) -> list[RawDocument]:
    """Load every .md file in a directory as a RawDocument of the given type."""
    docs: list[RawDocument] = []
    if not directory.exists():
        return docs
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        docs.append(
            RawDocument(
                doc_id=_doc_id_for(path),
                source_path=str(path),
                doc_type=doc_type,
                title=_extract_title(text, path.stem),
                text=text,
                metadata={"filename": path.name},
            )
        )
    return docs


def load_all_sources(data_dir: Path) -> list[RawDocument]:
    """Load runbooks, postmortems, and API docs from the standard data layout."""
    docs: list[RawDocument] = []
    docs += load_markdown_dir(data_dir / "runbooks", "runbook")
    docs += load_markdown_dir(data_dir / "postmortems", "postmortem")
    docs += load_markdown_dir(data_dir / "api_docs", "api_doc")
    return docs
