"""
Prompt registry.

Prompts are versioned files, not inline strings, so a prompt change is a
reviewable diff and every generated answer can be traced back to the exact
prompt text that produced it (logged as `prompt_version` + `prompt_hash` on
every query event). This is the same discipline as model/config versioning
in any serious MLOps setup, applied to the artifact that most influences
behavior in an LLM system: the prompt.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent / "prompts"


@lru_cache(maxsize=None)
def load_system_prompt(version: str) -> tuple[str, str]:
    """Returns (prompt_text, content_hash) for a given prompt version."""
    path = _PROMPTS_DIR / f"system_{version}.md"
    if not path.exists():
        available = [p.stem for p in _PROMPTS_DIR.glob("system_*.md")]
        raise ValueError(f"Unknown prompt version '{version}'. Available: {available}")
    text = path.read_text(encoding="utf-8")
    content_hash = hashlib.sha256(text.encode()).hexdigest()[:12]
    return text, content_hash


def build_user_message(question: str, retrieved_chunks: list) -> str:
    """Assemble the user turn: question + labeled, citable context blocks."""
    context_blocks = []
    for c in retrieved_chunks:
        meta = c.metadata
        context_blocks.append(
            f"[chunk_id: {c.chunk_id}] (source: {meta['title']} > {meta['section']}, type: {meta['doc_type']})\n"
            f"{c.text}"
        )
    context_str = "\n\n---\n\n".join(context_blocks) if context_blocks else "(no context retrieved)"
    return (
        f"Retrieved context:\n\n{context_str}\n\n"
        f"---\n\nQuestion: {question}"
    )
