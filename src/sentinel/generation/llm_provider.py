"""
LLM providers.

AnthropicProvider calls Claude directly. MockProvider is a deterministic
stand-in used in tests and CI so the whole pipeline (retrieval -> prompting
-> guardrails -> API) is exercisable without an API key or network call —
this is what makes `pytest` and the eval harness runnable in a clean
checkout with zero configuration.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from tenacity import retry, stop_after_attempt, wait_exponential

from sentinel.config import settings


@dataclass
class LLMResponse:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    stop_reason: str


class LLMProvider(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int) -> LLMResponse: ...


class AnthropicProvider(LLMProvider):
    def __init__(self):
        import anthropic

        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Set LLM_PROVIDER=mock for offline mode, "
                "or provide a key in .env."
            )
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    def complete(self, system: str, user: str, max_tokens: int) -> LLMResponse:
        resp = self.client.messages.create(
            model=settings.llm_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        return LLMResponse(
            text=text,
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
            model=resp.model,
            stop_reason=resp.stop_reason,
        )


class MockProvider(LLMProvider):
    """
    Deterministic offline stand-in.

    Produces a structurally valid answer (grounded sentences citing the
    provided chunk ids) purely from the retrieved context, so guardrail and
    citation-verification logic can be tested without a live model. It does
    NOT reason — it is a plumbing test double, not a quality benchmark.
    """

    def complete(self, system: str, user: str, max_tokens: int) -> LLMResponse:
        chunk_ids = re.findall(r"\[chunk_id:\s*([^\]]+)\]", user)
        if not chunk_ids:
            text = "INSUFFICIENT_CONTEXT: No retrieved context was provided to answer from."
        else:
            first_two = chunk_ids[:2]
            cite = ", ".join(f"[{c}]" for c in first_two)
            text = (
                f"Based on the retrieved runbook context {cite}, follow the documented "
                f"remediation steps in order, confirming each precondition before proceeding."
            )
        approx_in = max(1, len(user) // 4)
        approx_out = max(1, len(text) // 4)
        return LLMResponse(
            text=text, input_tokens=approx_in, output_tokens=approx_out, model="mock-v1", stop_reason="end_turn"
        )


def get_llm_provider() -> LLMProvider:
    if settings.llm_provider == "anthropic":
        return AnthropicProvider()
    return MockProvider()
