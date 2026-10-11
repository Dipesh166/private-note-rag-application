from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from app.api.deps import registry_dep, settings_dep
from app.api.schemas.common import OkOut
from app.api.schemas.document import DocumentListOut, DocumentOut, UploadResponse
from app.config import Settings, get_settings
from app.core.security import (
    UploadValidationError,
    safe_storage_name,
    sha256_hex,
    validate_upload,
)
from app.domain.models import Document
from app.infrastructure.registry.json_registry import DocumentRegistry
from app.services import ingestion_service

router = APIRouter(prefix="/documents", tags=["documents"])

def _to_out(doc: Document) -> DocumentOut:
    return DocumentOut(
        doc_id=doc.doc_id,
        filename=doc.filename,
        status=doc.status,
        pages=doc.pages,
        chunks=doc.chunks,
        error=doc.error,
        ingested_at=doc.ingested_at,
    )

def _index_background(doc: Document, saved_path: Path) -> None:
    try:
        ingestion_service.index(doc, saved_path, get_settings())
    except Exception:
        pass

@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload and index a document (PDF / Markdown / TXT)",
)
async def upload_document(
    background: BackgroundTasks,
    file: UploadFile = File(..., description=".pdf, .md or .txt"),
    settings: Settings = Depends(settings_dep),
    registry: DocumentRegistry = Depends(registry_dep),
) -> UploadResponse:
    content = await file.read()

    if len(content) > settings.max_upload_bytes:
        raise UploadValidationError(
            f"File exceeds the {settings.max_upload_mb} MB limit."
        )

    filename = file.filename or "upload"
    validate_upload(filename, content, settings)

    digest = sha256_hex(content)
    existing = registry.find_by_hash(digest)
    if existing is not None:
        return UploadResponse(
            doc_id=existing.doc_id,
            filename=existing.filename,
            status=existing.status,
            duplicate=True,
        )

    saved = settings.upload_dir / safe_storage_name(filename)
    saved.write_bytes(content)

    doc, _ = ingestion_service.prepare(saved, filename, content)
    background.add_task(_index_background, doc, saved)

    return UploadResponse(
        doc_id=doc.doc_id,
        filename=doc.filename,
        status=doc.status,
        duplicate=False,
    )

@router.get("", response_model=DocumentListOut, summary="List indexed documents")
def list_documents(registry: DocumentRegistry = Depends(registry_dep)) -> DocumentListOut:
    docs = [_to_out(d) for d in registry.list()]
    return DocumentListOut(documents=docs, total=len(docs))

@router.get("/{doc_id}", response_model=DocumentOut, summary="Document status")
def get_document(
    doc_id: str, registry: DocumentRegistry = Depends(registry_dep)
) -> DocumentOut:
    doc = registry.get(doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail=f"No document with id {doc_id}")
    return _to_out(doc)

@router.delete("/{doc_id}", response_model=OkOut, summary="Delete a document")
def delete_document(doc_id: str) -> OkOut:
    if not ingestion_service.remove(doc_id):
        raise HTTPException(status_code=404, detail=f"No document with id {doc_id}")
    return OkOut(detail=f"Deleted {doc_id}", removed=1)
