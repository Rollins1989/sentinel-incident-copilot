import os
import sys
from pathlib import Path

os.environ["ADMIN_TOKEN"] = "test-secret"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastapi.testclient import TestClient
from sentinel.api.main import app

client = TestClient(app)

def test_admin_token_rejects_missing_token():
    response = client.post("/ingest")
    assert response.status_code == 401

def test_security_headers_are_present():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"
