from __future__ import annotations

import json
import threading
from pathlib import Path

from app.config import get_settings
from app.domain.enums import DocumentStatus
from app.domain.models import Document

_lock = threading.Lock()

class DocumentRegistry:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or get_settings().registry_file

    def _load(self) -> dict[str, dict]:
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            backup = self._path.with_suffix(".corrupt.json")
            self._path.replace(backup)
            return {}
        return data if isinstance(data, dict) else {}

    def get(self, doc_id: str) -> Document | None:
        with _lock:
            raw = self._load().get(doc_id)
        return Document.from_dict(raw) if raw else None

    def list(self) -> list[Document]:
        with _lock:
            raw = self._load().values()
        return sorted(
            (Document.from_dict(item) for item in raw),
            key=lambda d: d.ingested_at,
            reverse=True,
        )

    def find_by_hash(self, sha256: str) -> Document | None:
        with _lock:
            raw = self._load().values()
        for item in raw:
            if item.get("sha256") == sha256:
                return Document.from_dict(item)
        return None

    def upsert(self, doc: Document) -> None:
        with _lock:
            data = self._load()
            data[doc.doc_id] = doc.to_dict()
            self._write(data)

    def set_status(
        self,
        doc_id: str,
        status: DocumentStatus,
        *,
        error: str | None = None,
        pages: int | None = None,
        chunks: int | None = None,
    ) -> Document | None:
        with _lock:
            data = self._load()
            raw = data.get(doc_id)
            if raw is None:
                return None
            doc = Document.from_dict(raw)
            doc.status = status
            doc.error = error
            if pages is not None:
                doc.pages = pages
            if chunks is not None:
                doc.chunks = chunks
            data[doc_id] = doc.to_dict()
            self._write(data)
            return doc

    def delete(self, doc_id: str) -> bool:
        with _lock:
            data = self._load()
            if doc_id not in data:
                return False
            del data[doc_id]
            self._write(data)
            return True

    def clear(self) -> int:
        with _lock:
            data = self._load()
            count = len(data)
            self._write({})
        return count

    def __len__(self) -> int:
        return len(self._load())

    def _write(self, data: dict[str, dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        tmp.replace(self._path)

_registry: DocumentRegistry | None = None

def get_registry() -> DocumentRegistry:
    global _registry
    if _registry is None:
        _registry = DocumentRegistry()
    return _registry
