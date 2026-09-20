# Sentinel — Engineering Knowledge Copilot

> Production-style RAG for incident response: hybrid retrieval, deterministic refusal guardrails, citation verification, evaluation, observability, and an operator console.

[![CI](https://github.com/Rollins1989/sentinel-incident-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/Rollins1989/sentinel-incident-copilot/actions/workflows/ci.yml)

## What it does

Sentinel answers on-call questions from indexed **runbooks, postmortems, and API documentation** instead of relying on generic model knowledge.

The request path is intentionally conservative:

1. **Ingest** — load Markdown, redact secrets/PII, preserve headings, and chunk documents.
2. **Retrieve** — run dense and BM25 lexical search independently.
3. **Fuse** — combine rankings with Reciprocal Rank Fusion.
4. **Refuse early** — reject weak or clearly out-of-scope evidence before an LLM call.
5. **Generate** — produce an answer with mandatory chunk citations.
6. **Verify** — deterministically validate citations against retrieved context.
7. **Sanitize** — redact sensitive output as defense in depth.
8. **Observe** — persist latency, token, confidence, refusal, cost, and trace data.

## Architecture

```
Markdown corpus
     │
     ▼
redact → structure-aware chunking
     │
     ├───────────────┐
     ▼               ▼
BM25            embeddings
     │               │
     └──── RRF ──────┘
             │
             ▼
       refusal policy
        │          │
      refuse      pass
        │          ▼
        │      LLM provider
        │          ▼
        │   citation verification
        │          ▼
        └──────► safe answer
```

## Engineering features

- **Hybrid retrieval:** BM25 preserves exact operational tokens while embeddings handle paraphrased questions.
- **Early refusal:** unsupported questions can be rejected without an LLM call.
- **Citation verification:** fabricated chunk IDs become a safety failure instead of being silently trusted.
- **Output redaction:** leaked secret/PII patterns are sanitized again after generation.
- **Provider abstraction:** deterministic offline providers make CI reproducible without API keys.
- **Prompt versioning:** prompts are content-hashed and recorded with every query.
- **Observability:** structured JSON logs, request IDs, SQLite metrics, and a metrics endpoint.
- **Readiness checks:** /health is liveness; /ready verifies the dense and sparse indexes are actually usable.
- **Admin protection:** /ingest accepts an optional X-Sentinel-Admin-Token when ADMIN_TOKEN is configured.
- **CI/CD:** unit tests, eval gates, Ruff linting, CodeQL, dependency caching, and Dependabot are included.

## API

| Endpoint | Purpose |
|---|---|
| GET /health | Liveness/config information |
| GET /ready | Retrieval readiness |
| POST /ask | Grounded incident question answering |
| POST /ingest | Rebuild indexes; optionally admin-protected |
| POST /feedback | Record human feedback |
| GET /metrics | Recent operational summary |
| GET /docs | OpenAPI/Swagger UI |

Example:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Our database connection pool is exhausted during peak traffic. What is the remediation?"}'
```

## Quickstart

```bash
git clone https://github.com/Rollins1989/sentinel-incident-copilot.git
cd sentinel-incident-copilot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

make ingest
make test
make eval
make run
```

Open http://localhost:8000.

## Real-model configuration

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=...
EMBEDDING_PROVIDER=sentence-transformer

CORS_ORIGINS=https://sentinel.example.com
ALLOWED_HOSTS=sentinel.example.com
ADMIN_TOKEN=replace-with-a-secret
ENVIRONMENT=production
```

The hashing embedder is an offline test double, not a semantic-quality benchmark.

## Evaluation

The repository contains a golden dataset and CI regression gate for retrieval recall, refusal correctness, and groundedness. Run:

```bash
make eval
```

The goal is to make retrieval, refusal, and grounding contracts measurable rather than relying on demo screenshots.

## Project layout

```
src/sentinel/
  api/            FastAPI app, schemas, routers, security
  ingestion/      loaders, redaction, structure-aware chunking
  retrieval/      embeddings, BM25, Chroma, RRF
  generation/     LLM providers, prompt registry, answer engine
  guardrails/     refusal and citation verification
  observability/  tracing and SQLite metrics
  eval/           golden dataset and regression harness
  experiments/    lightweight experiment tracking
frontend/         static incident console
data/             sample runbooks, postmortems, API docs
tests/            offline pytest suite
.github/          CI, CodeQL, Dependabot
```

## Important limitation

This is a portfolio-grade reference implementation, not a drop-in production security boundary. A real deployment still needs identity/access control, durable index lifecycle management, secret management, rate limiting, TLS, backup/restore, and organization-specific evaluation data.
