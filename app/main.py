from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.router import api_router
from app.config import get_settings
from app.core.logging import configure_logging, install_request_logging

logger = logging.getLogger(__name__)

def _seed_plan_document() -> None:
    from app.core.security import sha256_hex
    from app.infrastructure.registry.json_registry import get_registry
    from app.services import ingestion_service

    settings = get_settings()
    path = settings.seed_markdown
    if not path.exists():
        logger.info("no seed markdown at %s — skipping", path.name)
        return

    content = path.read_bytes()
    if get_registry().find_by_hash(sha256_hex(content)) is not None:
        return

    saved = settings.upload_dir / f"seed__{path.name}"
    saved.write_bytes(content)
    doc, _ = ingestion_service.prepare(saved, path.name, content)
    ingestion_service.index(doc, saved, settings)
    logger.info("seeded plan document: %s (%d chunks)", doc.filename, doc.chunks)

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.debug)

    threading.Thread(
        target=_warm_up, name="startup-warmup", daemon=True
    ).start()

    yield

    logger.info("shutdown — index persisted to %s", settings.chroma_dir)

def _warm_up() -> None:
    try:
        from app.infrastructure.vectorstore.chroma_store import get_vectorstore

        get_vectorstore()
        logger.info("chroma open: %s", get_settings().chroma_dir)
        _seed_plan_document()
    except Exception:
        logger.exception("vector store warm-up failed")

    try:
        from app.infrastructure.llm.hf_client import get_llm

        get_llm().warm_up()
    except Exception:
        logger.exception("LLM warm-up failed; it will load on first chat")

def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.debug)

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Local-first RAG API: upload PDFs/Markdown at runtime, index them "
            "into ChromaDB, and ask grounded questions with page-level citations. "
            "Everything runs on this machine — no cloud calls."
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )

    install_request_logging(app)
    register_error_handlers(app)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    def root():
        return {
            "service": settings.app_name,
            "docs": "/docs",
            "health": f"{settings.api_v1_prefix}/health",
        }

    return app

app = create_app()
