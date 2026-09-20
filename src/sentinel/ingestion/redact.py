"""Deterministic secret/PII redaction before indexing."""
from __future__ import annotations
import re

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("aws_secret_key", re.compile(r"(?i)aws_secret_access_key\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{40}['\"]?")),
    ("generic_api_key", re.compile(r"(?i)\b(api[_-]?key|token|secret)\b\s*[:=]\s*['\"]?[A-Za-z0-9_\-.]{16,}['\"]?")),
    ("private_key_block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]+?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("ipv4", re.compile(r"\b(?:10\.(?:\d{1,3}\.){2}\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.(?:\d{1,3}\.){1}\d{1,3}|192\.168\.(?:\d{1,3}\.)\d{1,3})\b")),
    ("phone", re.compile(r"\b\+?\d{1,2}[\s.-]?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")),
]

def redact(text: str) -> tuple[str, list[str]]:
    findings: list[str] = []
    output = text
    for label, pattern in _PATTERNS:
        if pattern.search(output):
            findings.append(label)
            output = pattern.sub(f"[REDACTED:{label.upper()}]", output)
    return output, findings
