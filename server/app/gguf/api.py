"""FastAPI routes for GGUF text generation with low-latency streaming."""
from __future__ import annotations

import json
from typing import AsyncIterator, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .runtime import RuntimeConfig, backend_snapshot, generate_text, stream_text

router = APIRouter(prefix="/v1", tags=["gguf"])


class SpeechRequest(BaseModel):
    input: str = Field(..., min_length=1, max_length=32768)
    stream: bool = False
    chunk_ms: Literal[20, 40, 80] = 40
    max_tokens: int = Field(256, ge=1, le=4096)
    response_format: Literal["text", "ndjson"] = "text"


@router.get("/gguf/health")
async def gguf_health() -> dict[str, object]:
    try:
        config = RuntimeConfig.from_env()
        model_exists = config.model_path.exists()
        profile = config.profile.name
    except Exception as exc:  # noqa: BLE001
        return {"ready": False, "error": str(exc), "backend": backend_snapshot()}
    return {"ready": model_exists, "model": str(config.model_path), "profile": profile, "backend": backend_snapshot()}


@router.post("/audio/speech")
async def create_speech(payload: SpeechRequest, request: Request) -> JSONResponse | StreamingResponse:
    """OpenAI-shaped endpoint.

    This repo has no TTS/audio decoder, so the endpoint streams text chunks from
    the GGUF model. Headers explicitly mark the stream as text to avoid claiming
    playable audio when no audio vocoder exists in the repository.
    """
    try:
        config = RuntimeConfig.from_env()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    if not payload.stream:
        try:
            text = await generate_text(config, payload.input, payload.max_tokens)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except RuntimeError as exc:
            status = 507 if "out of memory" in str(exc).lower() or "oom" in str(exc).lower() else 500
            raise HTTPException(status_code=status, detail=str(exc)) from exc
        return JSONResponse({"text": text, "audio_blocked": "No audio decoder/vocoder exists in this repository."})

    async def body() -> AsyncIterator[bytes]:
        try:
            async for chunk, elapsed in stream_text(config, payload.input, payload.max_tokens):
                if await request.is_disconnected():
                    break
                if payload.response_format == "ndjson":
                    yield (json.dumps({"delta": chunk.decode("utf-8", "replace"), "elapsed_s": elapsed}) + "\n").encode()
                else:
                    yield chunk
        except FileNotFoundError as exc:
            yield (json.dumps({"error": str(exc)}) + "\n").encode()
        except RuntimeError as exc:
            yield (json.dumps({"error": str(exc)}) + "\n").encode()

    media_type = "application/x-ndjson" if payload.response_format == "ndjson" else "text/plain; charset=utf-8"
    return StreamingResponse(
        body(),
        media_type=media_type,
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "X-Chunk-Ms": str(payload.chunk_ms),
            "X-Audio-Format": "unavailable-text-stream-only",
            "X-Sample-Rate": "0",
            "X-Channels": "0",
        },
    )
