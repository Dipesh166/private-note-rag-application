import sys

import httpx

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

QUESTIONS = [
    ("What embedding model does this project use?", None),
    ("What is retrieval augmented generation?", None),
    ("How are documents split into chunks before indexing?", None),
]

BASE = "http://127.0.0.1:8000"

def main() -> None:
    for q, doc_ids in QUESTIONS:
        payload = {"question": q, "top_k": 6}
        if doc_ids:
            payload["doc_ids"] = doc_ids
        r = httpx.post(f"{BASE}/v1/chat", json=payload, timeout=300)
        d = r.json()
        print("=" * 100)
        print("Q:", q)
        print("A:", d["answer"])
        print("retrieval_ms:", d["retrieval_ms"], "| sources:", len(d["sources"]))

        cited = None
        for s in d["sources"]:
            token = f"{s['filename']} · page {s['page']}"
            if token in d["answer"]:
                cited = s
                break
        if cited is None:
            print("CITATION: (none found in answer text)")
            continue

        print(f"CITED -> {cited['filename']} page {cited['page']} score {cited['score']}")
        print("EXCERPT OF THE CITED CHUNK:")
        print("   ", cited["excerpt"][:400])
        print("OTHER CANDIDATES (score | page | excerpt head):")
        for s in d["sources"]:
            mark = "<== CITED" if s is cited else ""
            print(f"    {s['score']:.3f}  p{s['page']:<4} {s['filename'][:28]:<28} "
                  f"{s['excerpt'][:110]!r} {mark}")

if __name__ == "__main__":
    main()
