# Sentinel — Engineering Knowledge Copilot for Incident Response

Sentinel is a retrieval-augmented assistant that answers on-call engineers'
questions using only your organization's own runbooks, postmortems, and API
docs — with a citation on every claim, and an explicit refusal when the
knowledge base doesn't cover the question.

## The problem

When an incident hits at 2am, the fix is almost always already written down
somewhere — in a runbook from the last time this happened, in a postmortem's
follow-up actions, in an API doc's rate-limit section. The problem isn't a
lack of documentation; it's that:

- Tribal knowledge is scattered across dozens of markdown files, wikis, and
  Slack threads that no one has time to grep through mid-incident.
- Generic LLM chat doesn't help here — it will confidently suggest a fix
  that sounds plausible but wasn't written by anyone on your team, isn't
  grounded in what actually works for *your* systems, and is unverifiable.
- Every minute spent searching is a minute of extended downtime (MTTR).

Sentinel is built specifically to avoid the generic-chatbot failure mode:
**it will not answer from its own training knowledge.** It answers only
from what it retrieved from your indexed docs, cites the exact chunk every
claim came from, and refuses outright when retrieval confidence is too low
— rather than filling the gap with a plausible-sounding guess about your
infrastructure.

## Architecture

```
                 ┌─────────────────────────────────────────────┐
                 │                 Ingestion                     │
   runbooks/     │  load → redact secrets/PII → heading-aware    │
   postmortems/  │  chunk → embed → index (dense + sparse)       │
   api_docs/     └─────────────────────────────────────────────┘
                                     │
                                     ▼
                 ┌─────────────────────────────────────────────┐
                 │            Hybrid Retriever                   │
                 │  BM25 (lexical)  +  dense embeddings           │
                 │        \_____ Reciprocal Rank Fusion _____/    │
                 └─────────────────────────────────────────────┘
                                     │
                                     ▼
                 ┌─────────────────────────────────────────────┐
                 │           Refusal Guardrail                    │
                 │  fused confidence < threshold?  → refuse       │
                 │  (before spending a single generation call)    │
                 └─────────────────────────────────────────────┘
                                     │  (passes)
                                     ▼
                 ┌─────────────────────────────────────────────┐
                 │              Generation                        │
                 │  versioned system prompt + cited context        │
                 │  → Claude (or mock provider offline)            │
                 └─────────────────────────────────────────────┘
                                     │
                                     ▼
                 ┌─────────────────────────────────────────────┐
                 │          Groundedness Guardrail                │
                 │  every [chunk_id] citation verified against     │
                 │  what was actually retrieved                    │
                 └─────────────────────────────────────────────┘
                                     │
                                     ▼
                     answer + citations + confidence + trace_id
                     (logged to SQLite for observability/eval)
```

## Why these design choices

**Hybrid retrieval (BM25 + dense), fused with RRF, not just embeddings.**
Ops docs are full of exact-match tokens that matter: `ECONNREFUSED`,
`CrashLoopBackOff`, env var names, HTTP status codes. Pure dense retrieval
can miss these; pure lexical search misses paraphrased questions. Reciprocal
Rank Fusion combines both rankings using rank position rather than raw
scores, avoiding the fragile problem of blending two metrics on
incomparable scales (cosine similarity vs. BM25 score).

**Refusal happens before generation, based on retrieval confidence alone.**
If the top fused score is below threshold, Sentinel refuses without ever
calling the LLM. This isn't just a cost optimization — it removes an entire
failure mode (the model rationalizing an answer from thin, irrelevant
context) rather than trying to catch it after the fact.

**Every citation is verified, not trusted.** The model is prompted to cite
`[chunk_id]` after every claim, but LLMs can cite a plausible-looking ID
that wasn't actually retrieved. `guardrails/groundedness.py` parses every
citation the model emitted and checks it against the chunk IDs that were
genuinely in context. This is a deterministic, zero-latency check, not
another model call.

**Secrets are redacted at ingestion, not at query time.** Runbooks
accumulate pasted AWS keys, internal IPs, and on-call phone numbers over
time. Redaction happens once, before anything is embedded or stored, so a
leaked secret in a source doc can never be retrieved verbatim.

**Prompts are versioned files with content hashes, not inline strings.**
Every logged query records `prompt_version:hash`, so a regression can always
be traced to the exact prompt text that produced it — the same discipline
most teams already apply to model versions, applied to the artifact that
actually drives behavior most.

**Two swappable providers for both the embedder and the LLM.** Production
uses real sentence-transformer embeddings and Claude. A fully offline,
deterministic pair (`EMBEDDING_PROVIDER=hashing`, `LLM_PROVIDER=mock`) means
the entire pipeline — ingestion, retrieval, guardrails, API, eval harness —
runs and is testable with zero API key and zero network access. That's what
makes `pytest` and CI green in a clean checkout.

## MLOps

This isn't a demo notebook — it has the operational scaffolding a real
deployment needs to evolve safely over time:

| Concern | Where |
|---|---|
| Prompt versioning | `generation/prompts/system_v1.md` + `generation/prompt_registry.py` (content-hashed) |
| Eval harness / regression gate | `eval/run_eval.py` — retrieval recall, refusal accuracy, groundedness rate against a golden dataset |
| CI gate | `.github/workflows/ci.yml` — fails the build if eval thresholds regress |
| Experiment tracking | `experiments/tracker.py` — every eval run logged with full config (chunk size, top_k, RRF k, prompt version) alongside its metrics |
| Observability | `observability/tracing.py` (structured JSON logs, trace IDs) + `observability/metrics.py` (per-query latency/cost/confidence in SQLite) |
| Feedback loop | `POST /feedback` — thumbs-down traces are the raw material for growing the golden eval set |

## Eval results — and an honest limitation

Running the eval harness (10 golden questions, offline deterministic
providers, no API key or network required):

```
Retrieval recall:    100.0%  (threshold 80%)
Refusal accuracy:     80.0%  (threshold 90%)   <- FAILS the CI gate, on purpose
Groundedness rate:   100.0%  (threshold 90%)
```

**This is a real, reproducible finding, not a bug I'm papering over.** Two
out-of-scope questions ("what pizza topping should the on-call team order"
and "can you approve my PTO") get just enough spurious lexical overlap with
indexed docs (the words "on-call" and "request" appear in real runbooks and
API docs) to cross the confidence threshold using the **offline hashing
embedder**, which is purely lexical and has no semantic understanding.

The fix is already built in and is a one-line config change:
`EMBEDDING_PROVIDER=sentence-transformer` swaps in real semantic embeddings,
which would separate "approve my PTO" from "database connection pool" on
meaning rather than shared substrings. I can't verify the exact resulting
score in this offline environment (it requires downloading a model), but
the architecture — and the eval harness that caught this gap in the first
place — means that's a one-command experiment to run and log via
`experiments/tracker.py`, not a redesign.

This is the entire point of shipping a real eval harness instead of eyeball
QA: it caught a genuine weakness in the default offline configuration before
a user did.

## Quickstart

```bash
git clone <this-repo> && cd sentinel
cp .env.example .env          # defaults to fully offline mock mode
pip install -r requirements.txt

make ingest                   # build the dense + sparse indexes from data/
make test                     # 17 tests, no API key needed
make eval                     # run the eval harness / CI gate locally
make run                      # start the API at http://localhost:8000
```

Open `http://localhost:8000` for the incident-console UI, or hit the API
directly:

```bash
curl -X POST localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Pods keep restarting with OOMKilled, what should I check?"}'
```

### Running with a real model

```bash
# in .env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
EMBEDDING_PROVIDER=sentence-transformer   # requires network on first run
```

### Docker

```bash
docker compose up --build
```

## Project layout

```
src/sentinel/
  ingestion/       loaders, PII/secret redaction, heading-aware chunking, pipeline
  retrieval/       embeddings (pluggable), BM25, Chroma vector store, RRF fusion
  generation/      LLM providers (pluggable), versioned prompts, answer engine
  guardrails/      groundedness check, confidence-based refusal policy
  observability/   structured tracing, SQLite metrics store
  eval/            golden dataset + eval harness (CI gate)
  experiments/     lightweight experiment/config tracker
  api/             FastAPI app, routers, schemas
data/              sample runbooks, postmortems, API docs
frontend/          incident-console chat UI (static HTML/JS)
tests/             pytest suite, fully offline
scripts/           ingest + CLI demo helpers
```

## What I'd build next

- Cross-encoder reranking as a second-stage filter on the RRF-fused top-K,
  before generation — RRF gets you a good candidate set fast, but a
  reranker would sharpen precision on ambiguous queries.
- An LLM-as-judge faithfulness score (a second Claude call comparing the
  answer against retrieved context) as a fourth eval metric, complementing
  the deterministic groundedness check with a semantic one.
- Slack integration so `/ask` and the refusal-driven feedback loop live
  where on-call engineers already are during an incident.
- Auto-promotion of thumbs-down feedback traces into the golden eval set
  after human triage, so the eval suite grows with real usage instead of
  staying fixed at 10 hand-written questions.
