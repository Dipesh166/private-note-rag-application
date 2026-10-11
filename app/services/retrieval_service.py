from __future__ import annotations

import logging

import numpy as np

from app.config import Settings, get_settings
from app.domain.constants import EXCERPT_CHARS
from app.domain.models import Source
from app.infrastructure.embeddings.minilm_embedder import get_embeddings
from app.infrastructure.vectorstore.chroma_store import get_vectorstore

logger = logging.getLogger(__name__)

def _normalize(text: str) -> str:
    return " ".join(text.split())

def _mmr_select(
    cand_vecs: np.ndarray,
    cand_scores: list[float],
    k: int,
    lambda_mult: float,
) -> list[int]:
    selected: list[int] = []
    remaining = list(range(len(cand_vecs)))

    while remaining and len(selected) < k:
        if not selected:
            best = max(remaining, key=lambda i: cand_scores[i])
        else:
            chosen = cand_vecs[selected]

            sims = cand_vecs @ chosen.T
            max_sim = sims.max(axis=1)
            mmr = lambda_mult * np.asarray(cand_scores) - (1 - lambda_mult) * max_sim
            best = max(remaining, key=lambda i: mmr[i])
        selected.append(best)
        remaining.remove(best)

    return selected

def retrieve(
    question: str,
    *,
    doc_ids: list[str] | None = None,
    top_k: int | None = None,
    settings: Settings | None = None,
) -> list[Source]:
    settings = settings or get_settings()
    store = get_vectorstore()
    embeddings = get_embeddings()

    k = top_k or settings.top_k
    fetch_k = max(settings.fetch_k, k)
    where = {"doc_id": {"$in": doc_ids}} if doc_ids else None

    query_vec = np.asarray(embeddings.embed_query(question), dtype=np.float32)

    results = store.similarity_search_by_vector_with_relevance_scores(
        query_vec, k=fetch_k, filter=where
    )
    if not results:
        logger.info("retrieval: no candidates for %r", question[:80])
        return []

    ids = [doc.metadata["chunk_id"] for doc, _ in results]
    stored = store._collection.get(ids=ids, include=["embeddings"])
    vec_map = {
        cid: np.asarray(vec, dtype=np.float32)
        for cid, vec in zip(stored["ids"], stored["embeddings"])
    }
    cand_vecs = np.stack([vec_map[cid] for cid in ids])
    relevances = cand_vecs @ query_vec

    triples = [
        (doc, float(rel), cand_vecs[i])
        for i, ((doc, _), rel) in enumerate(zip(results, relevances))
        if float(rel) >= settings.min_score
    ]
    dropped = len(results) - len(triples)
    if not triples:
        logger.info(
            "retrieval: all %d candidates below min_score=%.2f "
            "(best cosine=%.3f)",
            len(results),
            settings.min_score,
            float(relevances.max()) if len(relevances) else float("nan"),
        )
        return []

    scores = [rel for _, rel, _ in triples]
    kept_vecs = np.stack([vec for _, _, vec in triples])
    order = _mmr_select(kept_vecs, scores, min(k, len(triples)), settings.lambda_mult)

    sources: list[Source] = []
    for i in order:
        doc, score, _ = triples[i]
        meta = doc.metadata
        sources.append(
            Source(
                doc_id=meta.get("doc_id", ""),
                filename=meta.get("source", "unknown"),
                page=int(meta.get("page", 1)),
                chunk_id=meta.get("chunk_id", ""),
                excerpt=_normalize(doc.page_content)[:EXCERPT_CHARS],
                score=round(float(score), 4),
            )
        )

    logger.info(
        "retrieval: kept %d, dropped %d below floor, returned %d after MMR",
        len(triples),
        dropped,
        len(sources),
    )
    return sources
