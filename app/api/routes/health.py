from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import registry_dep, settings_dep
from app.api.schemas.common import HealthOut, OkOut
from app.config import Settings
from app.infrastructure.registry.json_registry import DocumentRegistry
from app.infrastructure.vectorstore.chroma_store import count, get_vectorstore
from app.services import ingestion_service

router = APIRouter(tags=["system"])

@router.get("/health", response_model=HealthOut, summary="Readiness of models and index")
def health(
    settings: Settings = Depends(settings_dep),
    registry: DocumentRegistry = Depends(registry_dep),
) -> HealthOut:
    docs = registry.list()
    loadable, ready = _llm_state()
    return HealthOut(
        llm=loadable,
        llm_ready=ready,
        llm_device=settings.resolved_llm_device,
        embedding_model=settings.embedding_model,
        indexed_docs=len(docs),
        total_chunks=count(get_vectorstore()),
    )

def _llm_state() -> tuple[bool, bool]:
    from app.infrastructure.llm.hf_client import get_llm

    try:
        if get_llm.cache_info().currsize == 0:
            return True, False
        return True, get_llm().ready
    except Exception:
        return False, False

@router.delete(
    "/knowledge-base",
    response_model=OkOut,
    summary="Clear ALL indexed data (requires confirm=true)",
)
def clear_knowledge_base(
    confirm: bool = Query(
        False,
        description="Must be true — guards against accidental wipes.",
    ),
) -> OkOut:
    if not confirm:
        return OkOut(
            detail="Refused: pass ?confirm=true to delete every document and vector.",
            removed=0,
        )
    removed = ingestion_service.clear_knowledge_base()
    return OkOut(detail=f"Cleared knowledge base ({removed} documents)", removed=removed)
