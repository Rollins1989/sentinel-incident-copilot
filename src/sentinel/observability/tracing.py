"""
Structured logging and request tracing.

Every request through the answer engine gets a trace_id that threads through
retrieval, generation, and guardrail checks. Logs are emitted as single-line
JSON so they can be shipped to any log aggregator (Datadog, CloudWatch, Loki)
without a custom parser — this is the minimum viable observability layer an
on-call engineer needs to answer "why did Sentinel say that?" after the fact.
"""
from __future__ import annotations

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar

_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")


def new_trace_id() -> str:
    tid = uuid.uuid4().hex[:12]
    _trace_id_var.set(tid)
    return tid


def current_trace_id() -> str:
    return _trace_id_var.get()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": round(time.time(), 3),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "trace_id": current_trace_id(),
        }
        # Include any extra fields passed via `extra=`
        reserved = set(vars(logging.LogRecord("", 0, "", 0, "", (), None)))
        for k, v in vars(record).items():
            if k not in reserved and k not in payload:
                try:
                    json.dumps(v)
                    payload[k] = v
                except TypeError:
                    payload[k] = str(v)
        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


class Timer:
    """Context manager that records elapsed wall time in milliseconds."""

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.elapsed_ms = round((time.perf_counter() - self._start) * 1000, 2)
