"""Orchestrates retrieval, refusal, generation, and deterministic safety checks."""
from __future__ import annotations

from dataclasses import dataclass, field

from sentinel.config import settings
from sentinel.generation.llm_provider import get_llm_provider
from sentinel.generation.prompt_registry import build_user_message, load_system_prompt
from sentinel.guardrails.groundedness import check_groundedness
from sentinel.guardrails.refusal_policy import REFUSAL_MESSAGE, evaluate_refusal
from sentinel.ingestion.redact import redact
from sentinel.observability.metrics import estimate_cost_usd, record_query_event
from sentinel.observability.tracing import Timer, get_logger, new_trace_id
from sentinel.retrieval.hybrid_retriever import HybridRetriever, RetrievedChunk

log = get_logger("answer_engine")


@dataclass
class Citation:
    chunk_id: str
    title: str
    section: str
    source_path: str
    doc_type: str


@dataclass
class AnswerResult:
    answer: str
    refused: bool
    refusal_reason: str | None
    citations: list[Citation]
    grounded: bool
    invalid_citations: list[str]
    confidence: float
    trace_id: str
    retrieved_chunks: list[RetrievedChunk] = field(default_factory=list)
    latency_ms: dict[str, float] = field(default_factory=dict)


class AnswerEngine:
    def __init__(self):
        self.retriever = HybridRetriever()
        self.llm = get_llm_provider()

    def answer(self, question: str, prompt_version: str | None = None) -> AnswerResult:
        question = question.strip()
        trace_id = new_trace_id()
        prompt_version = prompt_version or settings.prompt_version
        latencies: dict[str, float] = {}

        with Timer() as timer:
            retrieved = self.retriever.retrieve(question)
        latencies["retrieval_ms"] = timer.elapsed_ms

        decision = evaluate_refusal(retrieved, question)
        if decision.should_refuse:
            latencies["total_ms"] = latencies["retrieval_ms"]
            result = AnswerResult(
                answer=REFUSAL_MESSAGE,
                refused=True,
                refusal_reason=decision.reason,
                citations=[],
                grounded=True,
                invalid_citations=[],
                confidence=decision.top_score,
                trace_id=trace_id,
                retrieved_chunks=retrieved,
                latency_ms=latencies,
            )
            self._log_event(question, result, prompt_version, 0, 0)
            return result

        system_prompt, prompt_hash = load_system_prompt(prompt_version)
        user_message = build_user_message(question, retrieved)

        with Timer() as timer:
            llm_response = self.llm.complete(
                system_prompt, user_message, settings.max_answer_tokens
            )
        latencies["generation_ms"] = timer.elapsed_ms
        latencies["total_ms"] = latencies["retrieval_ms"] + latencies["generation_ms"]

        groundedness = check_groundedness(
            llm_response.text,
            [chunk.chunk_id for chunk in retrieved],
        )
        is_explicit_refusal = llm_response.text.strip().startswith("INSUFFICIENT_CONTEXT")
        safe_text, _ = redact(llm_response.text)

        if groundedness.invalid_citations:
            safe_text = REFUSAL_MESSAGE
            is_explicit_refusal = True
            refusal_reason = "invalid_citations"
        elif is_explicit_refusal:
            refusal_reason = "model_declined"
        else:
            refusal_reason = None

        citations = [
            Citation(
                chunk.chunk_id,
                chunk.metadata["title"],
                chunk.metadata["section"],
                chunk.metadata["source_path"],
                chunk.metadata["doc_type"],
            )
            for chunk in retrieved
            if chunk.chunk_id in groundedness.cited_chunk_ids
        ]
        result = AnswerResult(
            answer=safe_text,
            refused=is_explicit_refusal,
            refusal_reason=refusal_reason,
            citations=citations if not is_explicit_refusal else [],
            grounded=groundedness.is_grounded or is_explicit_refusal,
            invalid_citations=groundedness.invalid_citations,
            confidence=decision.top_score,
            trace_id=trace_id,
            retrieved_chunks=retrieved,
            latency_ms=latencies,
        )
        self._log_event(
            question,
            result,
            prompt_version,
            llm_response.input_tokens,
            llm_response.output_tokens,
            prompt_hash,
        )
        return result

    def _log_event(
        self,
        question,
        result,
        prompt_version,
        input_tokens,
        output_tokens,
        prompt_hash="",
    ):
        record_query_event(
            trace_id=result.trace_id,
            question=question,
            prompt_version=(
                f"{prompt_version}:{prompt_hash}" if prompt_hash else prompt_version
            ),
            retrieval_ms=result.latency_ms.get("retrieval_ms", 0.0),
            generation_ms=result.latency_ms.get("generation_ms", 0.0),
            total_ms=result.latency_ms.get(
                "total_ms", result.latency_ms.get("retrieval_ms", 0.0)
            ),
            confidence=result.confidence,
            refused=int(result.refused),
            n_chunks_retrieved=len(result.retrieved_chunks),
            retrieved_chunk_ids=[
                chunk.chunk_id for chunk in result.retrieved_chunks
            ],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimate_cost_usd(input_tokens, output_tokens),
        )
