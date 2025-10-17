from __future__ import annotations

import logging
import time
import uuid
from typing import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("restormer.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Record per-request diagnostics, including duration and request identifiers."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        start = time.perf_counter()
        context = {"request_id": request_id, "method": request.method, "path": request.url.path}
        try:
            response = await call_next(request)
        except Exception:  # noqa: BLE001
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception("Request failed", extra={**context, "duration_ms": round(duration_ms, 2)})
            raise
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "Request completed",
            extra={**context, "status_code": response.status_code, "duration_ms": round(duration_ms, 2)},
        )
        response.headers["x-request-id"] = request_id
        return response
