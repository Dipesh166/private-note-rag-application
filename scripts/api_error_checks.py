from __future__ import annotations

import sys
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"

def show(label: str, r: httpx.Response) -> None:
    print(f"{label:34s} -> {r.status_code}  {r.text[:150]}")

def main() -> int:
    if not httpx.get(f"{BASE}/v1/health", timeout=5).is_success:
        print("server not reachable")
        return 1

    print("== /v1/chat validation ==")
    show("too-short question", httpx.post(f"{BASE}/v1/chat", json={"question": "ab"}, timeout=30))
    show("valid question", httpx.post(f"{BASE}/v1/chat", json={"question": "Warranty period?"}, timeout=120))
    show("missing field", httpx.post(f"{BASE}/v1/chat", json={"ques": "x"}, timeout=30))
    show("whitespace question", httpx.post(f"{BASE}/v1/chat", json={"question": "   "}, timeout=30))
    show("top_k out of range", httpx.post(f"{BASE}/v1/chat", json={"question": "warranty", "top_k": 999}, timeout=30))
    show(
        "malformed JSON",
        httpx.post(
            f"{BASE}/v1/chat",
            content="{bad json",
            headers={"content-type": "application/json"},
            timeout=30,
        ),
    )

    print("\n== uploads ==")
    exe = Path("evil.exe")
    exe.write_bytes(b"MZ\x90\x00fake")
    with exe.open("rb") as fh:
        show("unsupported .exe", httpx.post(f"{BASE}/v1/documents/upload", files={"file": ("evil.exe", fh, "application/octet-stream")}, timeout=60))
    exe.unlink(missing_ok=True)

    fake = Path("fake.pdf")
    fake.write_bytes(b"definitely not a pdf")
    with fake.open("rb") as fh:
        show("fake pdf (magic bytes)", httpx.post(f"{BASE}/v1/documents/upload", files={"file": ("fake.pdf", fh, "application/pdf")}, timeout=60))
    fake.unlink(missing_ok=True)

    empty = Path("empty.pdf")
    empty.write_bytes(b"")
    with empty.open("rb") as fh:
        show("empty file", httpx.post(f"{BASE}/v1/documents/upload", files={"file": ("empty.pdf", fh, "application/pdf")}, timeout=60))
    empty.unlink(missing_ok=True)

    print("\n== resources ==")
    show("unknown doc GET", httpx.get(f"{BASE}/v1/documents/nope", timeout=30))
    show("unknown doc DELETE", httpx.delete(f"{BASE}/v1/documents/nope", timeout=30))
    show("KB clear w/o confirm", httpx.delete(f"{BASE}/v1/knowledge-base", timeout=30))

    print("\n== header echo ==")
    r = httpx.get(f"{BASE}/v1/health", headers={"x-request-id": "my-trace-1"}, timeout=30)
    print("x-request-id echoed:", r.headers.get("x-request-id"))

    return 0

if __name__ == "__main__":
    sys.exit(main())
