from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas.chat import ChatRequest, ChatResponse, SourceOut
from app.domain.models import ChatResult, Source
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])

def _to_out(source: Source) -> SourceOut:
    return SourceOut(
        doc_id=source.doc_id,
        filename=source.filename,
        page=source.page,
        chunk_id=source.chunk_id,
        excerpt=source.excerpt,
        score=source.score,
    )

def _to_response(result: ChatResult) -> ChatResponse:
    return ChatResponse(
        answer=result.answer,
        sources=[_to_out(s) for s in result.sources],
        retrieval_ms=result.retrieval_ms,
        model=result.model,
    )

@router.post("", response_model=ChatResponse, summary="Answer a question with citations")
def ask(request: ChatRequest) -> ChatResponse:
    result = chat_service.answer(
        request.question,
        doc_ids=request.doc_ids,
        top_k=request.top_k,
    )
    return _to_response(result)
