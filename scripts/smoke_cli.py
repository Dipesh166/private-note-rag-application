from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.domain.models import ChatResult
from app.services import chat_service

DEFAULT_QUESTIONS = [
    "What embedding model does this project use?",
    "What is the capital of France?",
    "Who created the Python programming language?",
    "What is the airspeed velocity of an unladen swallow?",
]

def show(question: str, result: ChatResult) -> None:
    print("\n" + "=" * 70)
    print(f"Q: {question}")
    print("-" * 70)
    print(f"A: {result.answer}")
    print(
        f"[model={result.model} | retrieval={result.retrieval_ms}ms | "
        f"sources={len(result.sources)}]"
    )
    for s in result.sources:
        print(f"   -> {s.filename} · page {s.page} (score {s.score})")

def main() -> int:
    questions = sys.argv[1:] or DEFAULT_QUESTIONS

    print(f"asking {len(questions)} question(s) — loading model on first answer...")
    started = time.perf_counter()
    results: list[tuple[str, ChatResult]] = []

    for q in questions:
        t0 = time.perf_counter()
        try:
            result = chat_service.answer(q)
            results.append((q, result))
            show(q, result)
            print(f"[total {(time.perf_counter() - t0):.1f}s]")
        except Exception as exc:
            print(f"\nQ: {q}\nERROR: {type(exc).__name__}: {exc}")
            return 1

    print("\n" + "=" * 70)
    print(f"all {len(results)} answered in {time.perf_counter() - started:.1f}s")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
