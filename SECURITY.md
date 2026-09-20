# Security Policy

## Reporting a vulnerability

Do not open a public GitHub issue for a suspected security vulnerability. Use GitHub's private security advisory mechanism for this repository or contact the repository owner directly.

## Deployment guidance

- Never commit .env files or real API keys.
- Set ADMIN_TOKEN before exposing POST /ingest outside a trusted network.
- Restrict CORS_ORIGINS to the actual frontend origins in production.
- Run the API behind TLS and a reverse proxy.
- Treat indexed runbooks, postmortems, and API docs as sensitive internal data.
- Review redaction findings before indexing a production corpus.
- Keep the offline/mock configuration for CI and never print provider secrets.
