from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.infrastructure.registry.json_registry import get_registry
from app.infrastructure.vectorstore.chroma_store import count, get_vectorstore
from app.services import ingestion_service

def main() -> int:
    settings = get_settings()
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else settings.seed_markdown

    if not target.exists():
        print(f"ERROR: file not found: {target}")
        return 1

    content = target.read_bytes()
    doc, is_duplicate = ingestion_service.prepare(target, target.name, content)

    if is_duplicate:
        print(f"DUPLICATE — already indexed as {doc.doc_id} "
              f"({doc.chunks} chunks, status={doc.status})")
    else:
        saved = settings.upload_dir / f"{doc.doc_id}__{target.name}"
        saved.write_bytes(content)
        doc = ingestion_service.index(doc, saved, settings)
        print(f"indexed {doc.filename!r} -> doc_id={doc.doc_id} "
              f"status={doc.status.value} pages={doc.pages} chunks={doc.chunks}")
        if doc.error:
            print(f"  ERROR: {doc.error}")

    print(f"chroma total chunks: {count(get_vectorstore())}")
    print(f"registry documents: {len(get_registry().list())}")
    return 0 if doc.status.value == "ready" else 1

if __name__ == "__main__":
    raise SystemExit(main())
