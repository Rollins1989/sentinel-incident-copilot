"""Run this once (or after adding new runbooks/postmortems/api_docs) to (re)build the indexes."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.ingestion.pipeline import run_ingestion

if __name__ == "__main__":
    result = run_ingestion()
    print(f"Ingested {result['n_docs']} documents into {result['n_chunks']} chunks "
          f"({result['redaction_events']} redaction events).")
