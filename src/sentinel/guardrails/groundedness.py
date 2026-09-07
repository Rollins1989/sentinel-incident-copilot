"""
Groundedness guardrail.

An LLM can cite a chunk_id that looks plausible but wasn't actually in the
retrieved context (a subtle hallucination mode that's easy to miss by eye).
This check parses every [chunk_id] the model emitted and verifies it
against the set that was actually retrieved. Any answer with an invalid
citation is flagged rather than silently trusted — this is a cheap,
deterministic check that catches a real failure mode without another LLM
call.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class GroundednessResult:
    is_grounded: bool
    cited_chunk_ids: list[str]
    invalid_citations: list[str]
    has_any_citation: bool


def check_groundedness(answer_text: str, retrieved_chunk_ids: list[str]) -> GroundednessResult:
    cited = re.findall(r"\[([^\[\]]+::\d+)\]", answer_text)
    valid_set = set(retrieved_chunk_ids)
    invalid = [c for c in cited if c not in valid_set]
    return GroundednessResult(
        is_grounded=len(invalid) == 0 and len(cited) > 0,
        cited_chunk_ids=cited,
        invalid_citations=invalid,
        has_any_citation=len(cited) > 0,
    )
