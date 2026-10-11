from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.domain.enums import DocumentStatus

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

@dataclass(slots=True)
class Source:
    doc_id: str
    filename: str
    page: int
    chunk_id: str
    excerpt: str
    score: float

    def label(self) -> str:
        return f"[{self.filename} · page {self.page}]"

@dataclass(slots=True)
class Document:
    doc_id: str
    filename: str
    sha256: str
    status: DocumentStatus = DocumentStatus.PROCESSING
    pages: int = 0
    chunks: int = 0
    error: str | None = None
    ingested_at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict:
        return {
            "doc_id": self.doc_id,
            "filename": self.filename,
            "sha256": self.sha256,
            "status": self.status.value,
            "pages": self.pages,
            "chunks": self.chunks,
            "error": self.error,
            "ingested_at": self.ingested_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Document":
        return cls(
            doc_id=data["doc_id"],
            filename=data["filename"],
            sha256=data["sha256"],
            status=DocumentStatus(data.get("status", DocumentStatus.PROCESSING)),
            pages=int(data.get("pages", 0)),
            chunks=int(data.get("chunks", 0)),
            error=data.get("error"),
            ingested_at=data.get("ingested_at", _utcnow()),
        )

@dataclass(slots=True)
class ChatResult:
    answer: str
    sources: list[Source]
    retrieval_ms: int
    model: str
