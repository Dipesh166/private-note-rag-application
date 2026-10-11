from __future__ import annotations

from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document as LC_Document
from langchain_core.embeddings import Embeddings

from app.config import Settings, get_settings
from app.infrastructure.embeddings.minilm_embedder import get_embeddings

MODEL_KEY = "embedding_model"
COLLECTION_NAME = "knowledge_base"

class EmbeddingModelMismatch(RuntimeError):
    pass

@lru_cache
def get_vectorstore() -> Chroma:
    settings = get_settings()
    store = _open_store(settings, get_embeddings())
    _verify_model_binding(store, settings)
    return store

def _open_store(settings: Settings, embeddings: Embeddings) -> Chroma:
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(settings.chroma_dir),
    )

def _verify_model_binding(store: Chroma, settings: Settings) -> None:
    collection = store._collection
    meta = collection.metadata or {}

    if not meta:
        collection.modify(metadata={MODEL_KEY: settings.embedding_model})
        return

    stored = meta.get(MODEL_KEY)
    if stored and stored != settings.embedding_model:
        raise EmbeddingModelMismatch(
            f"Vector store at {settings.chroma_dir} was built with "
            f"'{stored}' but the app is configured with "
            f"'{settings.embedding_model}'. Reindex all documents or "
            "restore the previous EMBEDDING_MODEL value."
        )

def add_chunks(store: Chroma, chunks: list[LC_Document]) -> None:
    if not chunks:
        return
    store.add_documents(
        documents=chunks,
        ids=[c.metadata["chunk_id"] for c in chunks],
    )

def delete_by_doc(store: Chroma, doc_id: str) -> int:
    collection = store._collection
    result = collection.get(where={"doc_id": doc_id})
    ids = result.get("ids", [])
    if ids:
        collection.delete(where={"doc_id": doc_id})
    return len(ids)

def count(store: Chroma) -> int:
    return store._collection.count()

def reset(store: Chroma) -> None:
    settings = get_settings()
    store.delete_collection()

    fresh = _open_store(settings, get_embeddings())
    _verify_model_binding(fresh, settings)

    get_vectorstore.cache_clear()
    get_vectorstore()
