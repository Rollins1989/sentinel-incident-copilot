"""
Answer engine: the orchestration layer that turns a question into a
grounded, cited answer (or an explicit refusal).

Pipeline:
    retrieve -> pre-generation refusal check -> prompt -> generate
    -> post-generation groundedness check -> log + return

Every step is timed and logged with a trace_id so a bad answer in
production can be root-caused: was it a retrieval miss, a refusal
threshold issue, or a citation the model fabricated?
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sentinel.config import settings
from sentinel.generation.llm_provider import get_llm_provider
from sentinel.generation.prompt_registry import build_user_message, load_system_prompt
from sentinel.guardrails.groundedness import check_groundedness
from sentinel.guardrails.refusal_policy import REFUSAL_MESSAGE, evaluate_refusal
from sentinel.observability.metrics import estimate_cost_usd, record_query_event
from sentinel.observability.tracing import Timer, current_trace_id, get_logger, new_trace_id
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
        trace_id = new_trace_id()
        prompt_version = prompt_version or settings.prompt_version
        latencies: dict[str, float] = {}

        with Timer() as t_retrieve:
            retrieved = self.retriever.retrieve(question)
        latencies["retrieval_ms"] = t_retrieve.elapsed_ms

        decision = evaluate_refusal(retrieved)
        if decision.should_refuse:
            log.info(
                "answer.refused",
                extra={"reason": decision.reason, "top_score": decision.top_score, "question": question},
            )
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
            self._log_event(question, result, prompt_version, input_tokens=0, output_tokens=0)
            return result

        system_prompt, prompt_hash = load_system_prompt(prompt_version)
        user_message = build_user_message(question, retrieved)

        with Timer() as t_gen:
            llm_response = self.llm.complete(system_prompt, user_message, settings.max_answer_tokens)
        latencies["generation_ms"] = t_gen.elapsed_ms
        latencies["total_ms"] = latencies["retrieval_ms"] + latencies["generation_ms"]

        retrieved_ids = [c.chunk_id for c in retrieved]
        groundedness = check_groundedness(llm_response.text, retrieved_ids)

        is_explicit_refusal = llm_response.text.strip().startswith("INSUFFICIENT_CONTEXT")

        citations = [
            Citation(
                chunk_id=c.chunk_id,
                title=c.metadata["title"],
                section=c.metadata["section"],
                source_path=c.metadata["source_path"],
                doc_type=c.metadata["doc_type"],
            )
            for c in retrieved
            if c.chunk_id in groundedness.cited_chunk_ids
        ]

        result = AnswerResult(
            answer=llm_response.text,
            refused=is_explicit_refusal,
            refusal_reason="model_declined" if is_explicit_refusal else None,
            citations=citations,
            grounded=groundedness.is_grounded or is_explicit_refusal,
            invalid_citations=groundedness.invalid_citations,
            confidence=decision.top_score,
            trace_id=trace_id,
            retrieved_chunks=retrieved,
            latency_ms=latencies,
        )

        if groundedness.invalid_citations:
            log.warning(
                "answer.invalid_citations",
                extra={"invalid": groundedness.invalid_citations, "question": question},
            )

        log.info(
            "answer.generated",
            extra={
                "question": question,
                "grounded": result.grounded,
                "n_citations": len(citations),
                "confidence": decision.top_score,
                **latencies,
            },
        )

        self._log_event(
            question, result, prompt_version, llm_response.input_tokens, llm_response.output_tokens, prompt_hash
        )
        return result

    def _log_event(self, question, result: AnswerResult, prompt_version, input_tokens, output_tokens, prompt_hash=""):
        record_query_event(
            trace_id=result.trace_id,
            question=question,
            prompt_version=f"{prompt_version}:{prompt_hash}" if prompt_hash else prompt_version,
            retrieval_ms=result.latency_ms.get("retrieval_ms", 0.0),
            generation_ms=result.latency_ms.get("generation_ms", 0.0),
            total_ms=result.latency_ms.get("total_ms", result.latency_ms.get("retrieval_ms", 0.0)),
            confidence=result.confidence,
            refused=int(result.refused),
            n_chunks_retrieved=len(result.retrieved_chunks),
            retrieved_chunk_ids=[c.chunk_id for c in result.retrieved_chunks],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimate_cost_usd(input_tokens, output_tokens),
        )
