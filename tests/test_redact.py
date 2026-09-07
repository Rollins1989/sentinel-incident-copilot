import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.ingestion.redact import redact


def test_redacts_aws_key():
    text = "Access key: AKIAABCDEFGHIJKLMNOP is leaked here."
    clean, findings = redact(text)
    assert "AKIAABCDEFGHIJKLMNOP" not in clean
    assert "aws_access_key" in findings


def test_redacts_email():
    clean, findings = redact("Contact oncall-engineer@company.com for help.")
    assert "oncall-engineer@company.com" not in clean
    assert "email" in findings


def test_leaves_clean_text_untouched():
    text = "Restart the pod using kubectl delete pod my-pod-123."
    clean, findings = redact(text)
    assert clean == text
    assert findings == []
