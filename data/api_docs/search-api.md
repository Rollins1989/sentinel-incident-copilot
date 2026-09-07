# Internal Search API

## Overview
Provides full-text and vector search over internal documents for other
services to build on (Sentinel itself is a consumer of this API in
production deployments where a shared search backend already exists).

## Authentication
Requires an API key passed as `X-API-Key` header, issued per-service by the
platform team.

## Rate Limits
Each API key is limited to **100 requests per minute**. Requests beyond
this limit receive a `429` response. There is no burst allowance — the
limit is a strict sliding window, not a token bucket.

## Endpoints
- `POST /v1/search` — body: `{"query": str, "top_k": int, "filters": {...}}`.
- `POST /v1/index` — index or re-index a document. Requires `index:write` scope.
