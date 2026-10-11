from __future__ import annotations

import logging
import time

from app.config import get_settings
from app.domain.models import ChatResult, Source
from app.infrastructure.llm.hf_client import HFTransformersClient, get_llm
from app.infrastructure.vectorstore.chroma_store import get_vectorstore
from app.prompts import rag_prompts
from app.services import retrieval_service

logger = logging.getLogger(__name__)

NO_CONTEXT_ANSWER = "Insufficient context to answer this question."

def _full_chunks(sources: list[Source]) -> list[tuple[str, str, int, str]]:
    if not sources:
        return []
    store = get_vectorstore()
    ids = [s.chunk_id for s in sources]
    got = store._collection.get(ids=ids, include=["documents", "metadatas"])

    by_id: dict[str, tuple[str, str, int, str]] = {}
    for cid, text, meta in zip(got["ids"], got["documents"], got["metadatas"]):
        by_id[cid] = (
            cid,
            meta.get("source", "unknown"),
            int(meta.get("page", 1)),
            text or "",
        )
    return [by_id[cid] for cid in ids if cid in by_id]

def answer(
    question: str,
    *,
    doc_ids: list[str] | None = None,
    top_k: int | None = None,
    llm: HFTransformersClient | None = None,
) -> ChatResult:
    settings = get_settings()
    llm = llm or get_llm()

    started = time.perf_counter()
    sources = retrieval_service.retrieve(
        question, doc_ids=doc_ids, top_k=top_k, settings=settings
    )
    retrieval_ms = int((time.perf_counter() - started) * 1000)

    if not sources:
        logger.info("no chunk met min_score; returning canned response")
        return ChatResult(
            answer=NO_CONTEXT_ANSWER,
            sources=[],
            retrieval_ms=retrieval_ms,
            model=llm.model_name,
        )

    context = rag_prompts.build_context(sources, _full_chunks(sources))
    user_prompt = rag_prompts.build_user_prompt(question, context)

    generated = llm.generate(rag_prompts.SYSTEM_PROMPT, user_prompt)

    answer_text = rag_prompts.normalize_citations(generated, sources)
    total_ms = int((time.perf_counter() - started) * 1000)

    logger.info(
        "answered in %d ms (retrieval %d ms) with %d sources",
        total_ms,
        retrieval_ms,
        len(sources),
    )
    return ChatResult(
        answer=answer_text,
        sources=sources,
        retrieval_ms=retrieval_ms,
        model=llm.model_name,
    )
