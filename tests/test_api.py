import os
import sys
from pathlib import Path

os.environ["LLM_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "hashing"
os.environ["CHROMA_PERSIST_DIR"] = ".chroma_test_api"

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastapi.testclient import TestClient

from sentinel.ingestion.pipeline import run_ingestion
from sentinel.api.main import app

client = TestClient(app)


def setup_module(module):
    run_ingestion(Path(__file__).resolve().parents[1] / "data")


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_ask_in_scope_question_returns_answer():
    res = client.post("/ask", json={"question": "The pod keeps restarting with OOMKilled, what should I do?"})
    assert res.status_code == 200
    data = res.json()
    assert "trace_id" in data
    assert isinstance(data["citations"], list)


def test_ask_out_of_scope_question_is_refused_or_flagged():
    res = client.post("/ask", json={"question": "xyzzy unrelated nonsense query zzqx"})
    assert res.status_code == 200
    data = res.json()
    # Either the confidence guardrail refuses it, or it comes back with low confidence.
    assert data["refused"] is True or data["confidence"] < 0.5


def test_ask_rejects_too_short_question():
    res = client.post("/ask", json={"question": "hi"})
    assert res.status_code == 422
