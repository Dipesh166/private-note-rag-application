from __future__ import annotations

import logging
from pathlib import Path

from app.config import Settings, get_settings
from app.core.security import sha256_hex
from app.domain.enums import DocumentStatus
from app.domain.models import Document
from app.infrastructure.chunking.recursive_splitter import chunk_documents
from app.infrastructure.loaders.base import get_loader
from app.infrastructure.registry.json_registry import get_registry
from app.infrastructure.vectorstore import chroma_store
from app.infrastructure.vectorstore.chroma_store import get_vectorstore

logger = logging.getLogger(__name__)

class EmptyDocumentError(RuntimeError):
    pass

def _new_doc_id(sha256: str) -> str:
    return sha256[:12]

def prepare(path: Path, filename: str, content: bytes) -> tuple[Document, bool]:
    registry = get_registry()
    digest = sha256_hex(content)

    existing = registry.find_by_hash(digest)
    if existing is not None:
        logger.info("duplicate upload skipped: %s (%s)", filename, existing.doc_id)
        return existing, True

    doc = Document(
        doc_id=_new_doc_id(digest),
        filename=filename,
        sha256=digest,
        status=DocumentStatus.PROCESSING,
    )
    registry.upsert(doc)
    logger.info("registered upload %s as %s", filename, doc.doc_id)
    return doc, False

def index(doc: Document, path: Path, settings: Settings | None = None) -> Document:
    settings = settings or get_settings()
    registry = get_registry()

    try:
        loader = get_loader(path)
        docs = loader.load(path)
        if not docs:
            raise EmptyDocumentError("No content was extracted from the file.")

        for d in docs:
            d.metadata["source"] = doc.filename

        chunks = chunk_documents(docs, settings, doc.doc_id)
        if not chunks:
            raise EmptyDocumentError("Document produced no chunks to index.")

        store = get_vectorstore()
        chroma_store.add_chunks(store, chunks)

        pages = max(int(d.metadata.get("page", 1)) for d in docs)
        updated = registry.set_status(
            doc.doc_id,
            DocumentStatus.READY,
            pages=pages,
            chunks=len(chunks),
        )
        logger.info(
            "indexed %s: %d pages, %d chunks", doc.filename, pages, len(chunks)
        )
        return updated or doc

    except EmptyDocumentError as exc:
        reason = (
            f"{exc} The file appears to be scanned or image-only; "
            "OCR is not enabled."
        )
        logger.warning("indexing failed for %s: %s", doc.filename, reason)
        registry.set_status(doc.doc_id, DocumentStatus.FAILED, error=reason)
        return registry.get(doc.doc_id) or doc

    except Exception as exc:
        logger.exception("indexing crashed for %s", doc.filename)
        registry.set_status(
            doc.doc_id,
            DocumentStatus.FAILED,
            error=f"{type(exc).__name__}: {exc}",
        )
        return registry.get(doc.doc_id) or doc
    finally:
        path.unlink(missing_ok=True)

def remove(doc_id: str) -> bool:
    removed = chroma_store.delete_by_doc(get_vectorstore(), doc_id)
    deleted = get_registry().delete(doc_id)
    logger.info("removed %s (%d chunks)", doc_id, removed)
    return deleted

def clear_knowledge_base() -> int:
    store = get_vectorstore()
    chroma_store.reset(store)
    return get_registry().clear()
