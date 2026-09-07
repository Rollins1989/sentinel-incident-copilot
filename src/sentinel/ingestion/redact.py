"""
Redaction pass.

Runbooks and postmortems are exactly the kind of internal document that
accumulates secrets over time: a pasted AWS key during an incident, an
internal IP, an on-call phone number. Sentinel redacts these *before*
anything is embedded or stored, and again as a defense-in-depth check on
LLM output, so a leaked secret in a source doc can't be retrieved verbatim
or echoed back in an answer.

This is intentionally simple, fast regex-based redaction rather than an
ML-based PII detector: for an internal ops corpus, precision on known
secret *shapes* (keys, tokens, IPs, emails) matters more than fuzzy recall,
and regex is auditable and has zero inference cost on every ingested doc.
"""
from __future__ import annotations

import re

_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws_secret_key", re.compile(r"(?i)aws_secret_access_key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?")),
    ("generic_api_key", re.compile(r"(?i)\b(api[_-]?key|token|secret)\b\s*[:=]\s*['\"]?[A-Za-z0-9\-_\.]{16,}['\"]?")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("ipv4", re.compile(r"\b(?:10|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
    ("phone", re.compile(r"\b\+?\d{1,2}[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")),
]


def redact(text: str) -> tuple[str, list[str]]:
    """Return (redacted_text, list_of_finding_types). Deterministic and cheap."""
    findings: list[str] = []
    out = text
    for label, pattern in _PATTERNS:
        if pattern.search(out):
            findings.append(label)
            out = pattern.sub(f"[REDACTED:{label.upper()}]", out)
    return out, findings
