"""Consistent error envelope + exception handlers.

Every error response is::

    {"error": {"code": "<machine_code>", "message": "<human message>",
               "request_id": "<uuid>", "details": <optional>}}
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("patentgate.api")

_STATUS_CODE_NAMES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    503: "service_unavailable",
}


def _envelope(request: Request, status_code: int, code: str, message: str, details=None) -> JSONResponse:
    body = {
        "error": {
            "code": code,
            "message": message,
            "request_id": getattr(request.state, "request_id", None),
        }
    }
    if details is not None:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http_exception(request: Request, exc: StarletteHTTPException):
        code = _STATUS_CODE_NAMES.get(exc.status_code, "error")
        return _envelope(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(HTTPException)
    async def _fastapi_http_exception(request: Request, exc: HTTPException):
        code = _STATUS_CODE_NAMES.get(exc.status_code, "error")
        return _envelope(request, exc.status_code, code, str(exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        return _envelope(
            request,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "validation_error",
            "Request validation failed",
            details=[
                {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]}
                for e in exc.errors()
            ],
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception):
        logger.exception("unhandled error", extra={"path": request.url.path})
        return _envelope(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "internal_error",
            "An unexpected error occurred.",
        )
