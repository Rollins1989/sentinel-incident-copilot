"""Quick CLI demo: ask Sentinel a question from the terminal without starting the API."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sentinel.generation.answer_engine import AnswerEngine

QUESTIONS = [
    "The API is returning 502s and pods keep restarting, what should I check?",
    "What's the maximum retry backoff for the notifications API?",
    "Can you approve my vacation request?",
]

if __name__ == "__main__":
    engine = AnswerEngine()
    question = sys.argv[1] if len(sys.argv) > 1 else QUESTIONS[0]
    result = engine.answer(question)
    print(f"\nQ: {question}\n")
    print(f"A: {result.answer}\n")
    print(f"Refused: {result.refused} | Grounded: {result.grounded} | Confidence: {result.confidence:.3f}")
    print(f"Citations: {[c.chunk_id for c in result.citations]}")
    print(f"Trace ID: {result.trace_id}")
