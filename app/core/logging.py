from __future__ import annotations

import logging
import sys
import time
import uuid

from fastapi import FastAPI, Request

FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
DATEFMT = "%H:%M:%S"

def configure_logging(debug: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format=FORMAT,
        datefmt=DATEFMT,
        stream=sys.stdout,
        force=True,
    )

    for noisy in ("httpx", "httpcore", "chromadb", "sentence_transformers", "transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

def install_request_logging(app: FastAPI) -> None:
    @app.middleware("http")
    async def _log(request: Request, call_next):
        request_id = request.headers.get("x-request-id", uuid.uuid4().hex[:12])
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed = (time.perf_counter() - started) * 1000
            logging.getLogger("access").error(
                "%s %s -> 500 (%.0f ms) rid=%s",
                request.method, request.url.path, elapsed, request_id,
            )
            raise
        elapsed = (time.perf_counter() - started) * 1000
        logging.getLogger("access").info(
            "%s %s -> %d (%.0f ms) rid=%s",
            request.method, request.url.path, response.status_code, elapsed, request_id,
        )
        response.headers["x-request-id"] = request_id
        return response
