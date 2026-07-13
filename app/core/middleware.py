"""
ASGI middleware: request IDs and a hard body-size guard.

The body-size guard rejects oversized requests based on the ``Content-Length``
header *before* the body is read into memory - closing the memory-exhaustion
hole where uploads were fully buffered before the size limit was checked.
"""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request ID, bind it to the logger, and echo it in responses."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.unbind_contextvars("request_id")
        response.headers["X-Request-ID"] = request_id
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose declared body exceeds the configured maximum."""

    def __init__(self, app, max_bytes: int) -> None:
        super().__init__(app)
        self._max = max_bytes

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self._max:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": (
                                f"Request body exceeds the maximum of "
                                f"{self._max // (1024 * 1024)} MB."
                            ),
                            "status_code": 413,
                        },
                    )
            except ValueError:
                pass
        return await call_next(request)
