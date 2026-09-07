# Internal Billing API

## Authentication
All requests to the billing API require an `Authorization: Bearer <token>`
header, where the token is a service-to-service JWT issued by the internal
auth service (`auth.internal:8443/token`) with the `billing:read` or
`billing:write` scope. Tokens expire after 15 minutes and must be refreshed
by the caller; the billing API does not auto-refresh.

## Endpoints
- `GET /v1/invoices/{customer_id}` — list invoices for a customer. Requires `billing:read`.
- `POST /v1/charges` — create a new charge. Requires `billing:write`. Idempotent when an `Idempotency-Key` header is provided.
- `POST /v1/refunds` — issue a refund. Requires `billing:write` and an additional `refunds:approve` scope for amounts over $500.

## Error Codes
- `401` — missing or expired token.
- `403` — token valid but missing required scope.
- `409` — idempotency key reused with a different request body.
