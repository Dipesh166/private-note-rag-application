from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import DocumentStatus

class UploadResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "doc_id": "8cba06955379",
            "filename": "notes.pdf",
            "status": "processing",
            "duplicate": False,
        }
    })

    doc_id: str
    filename: str
    status: DocumentStatus
    duplicate: bool = Field(
        default=False,
        description="True when this exact file content was already indexed",
    )

class DocumentOut(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "doc_id": "8cba06955379",
            "filename": "notes.pdf",
            "status": "ready",
            "pages": 3,
            "chunks": 3,
            "error": None,
            "ingested_at": "2026-10-10T14:00:00+00:00",
        }
    })

    doc_id: str
    filename: str
    status: DocumentStatus
    pages: int = 0
    chunks: int = 0
    error: str | None = None
    ingested_at: str

class DocumentListOut(BaseModel):
    documents: list[DocumentOut]
    total: int
