from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

BASE = "http://127.0.0.1:8000"

def main() -> int:
    r = httpx.delete(f"{BASE}/v1/documents/17cbbdb4b154", timeout=60)
    print("DELETE:", r.status_code, r.text)

    h = httpx.get(f"{BASE}/v1/health", timeout=60).json()
    print(f"after delete -> docs: {h['indexed_docs']} chunks: {h['total_chunks']}")

    d = httpx.get(f"{BASE}/v1/documents/17cbbdb4b154", timeout=30)
    print("GET deleted doc ->", d.status_code)

    import chromadb
    from app.config import get_settings

    client = chromadb.PersistentClient(path=str(get_settings().chroma_dir))
    col = client.get_collection("knowledge_base")
    got = col.get(where={"doc_id": "17cbbdb4b154"}, include=["metadatas"])
    print(f"chroma chunks for deleted doc: {len(got['ids'])} (expect 0)")

    docs = httpx.get(f"{BASE}/v1/documents", timeout=30).json()
    print(f"\nfinal state ({docs['total']} documents):")
    for x in docs["documents"]:
        print(
            f"   {x['doc_id']}  {x['status']:8s} "
            f"pages={x['pages']} chunks={x['chunks']}  {x['filename'][:45]}"
        )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
