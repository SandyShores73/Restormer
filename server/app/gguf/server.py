"""Standalone GGUF FastAPI server entrypoint.

Run with:
    uvicorn server.app.gguf.server:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import logging

from fastapi import FastAPI

from .api import router
from .runtime import backend_snapshot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("restormer.gguf")

app = FastAPI(title="Restormer GGUF Runtime", version="1.0.0")
app.include_router(router)


@app.on_event("startup")
async def log_backend() -> None:
    logger.info("GGUF backend snapshot: %s", backend_snapshot())
