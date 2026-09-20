"""Structured JSON logging plus request/answer trace IDs."""
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

def set_trace_id(trace_id: str) -> str:
    _trace_id_var.set(trace_id)
    return trace_id

def current_trace_id() -> str:
    return _trace_id_var.get()

class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"ts": round(time.time(), 3), "level": record.levelname, "logger": record.name, "event": record.getMessage(), "trace_id": current_trace_id()}
        reserved = set(vars(logging.LogRecord("", 0, "", 0, "", (), None)))
        for key, value in vars(record).items():
            if key not in reserved and key not in payload:
                try:
                    json.dumps(value)
                    payload[key] = value
                except TypeError:
                    payload[key] = str(value)
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
    def __enter__(self):
        self._start = time.perf_counter()
        return self
    def __exit__(self, *exc):
        self.elapsed_ms = round((time.perf_counter() - self._start) * 1000, 2)
