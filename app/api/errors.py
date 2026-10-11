from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.security import UploadValidationError
from app.infrastructure.llm.errors import GenerationError
from app.infrastructure.vectorstore.chroma_store import EmbeddingModelMismatch

logger = logging.getLogger(__name__)

def _envelope(status: int, detail: str, code: str, request: Request) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "-")
    logger.error("[%s] %s -> %s: %s", request_id, code, status, detail)
    return JSONResponse(
        status_code=status,
        content={"detail": detail, "code": code},
    )

def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(UploadValidationError)
    async def _upload_invalid(request: Request, exc: UploadValidationError):
        return _envelope(400, str(exc), "invalid_upload", request)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError):
        errors = "; ".join(
            f"{'.'.join(str(p) for p in e.get('loc', []))}: {e.get('msg')}"
            for e in exc.errors()
        )
        return _envelope(422, errors, "validation_error", request)

    @app.exception_handler(GenerationError)
    async def _generation(request: Request, exc: GenerationError):
        return _envelope(503, str(exc), "generation_unavailable", request)

    @app.exception_handler(EmbeddingModelMismatch)
    async def _model_mismatch(request: Request, exc: EmbeddingModelMismatch):
        return _envelope(500, str(exc), "embedding_model_mismatch", request)

    @app.exception_handler(FileNotFoundError)
    async def _not_found(request: Request, exc: FileNotFoundError):
        return _envelope(404, str(exc), "not_found", request)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "-")
        logger.exception("[%s] unhandled error", request_id)
        return _envelope(
            500,
            "Internal server error",
            "internal_error",
            request,
        )
