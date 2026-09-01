"""Minimal in-process rate limiting as a FastAPI dependency.

A fixed-window counter keyed by ``(client-ip, bucket-name)``. Good enough for a
single-process deployment; put a shared store in front for multi-process. No
third-party dependency, no request-signature magic.
"""

from __future__ import annotations

import os
import threading
import time

from fastapi import Depends, HTTPException, Request, status

_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() != "false"


class _FixedWindow:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], tuple[int, float]] = {}
        self._lock = threading.Lock()

    def check(self, key: tuple[str, str], limit: int, window_seconds: float) -> tuple[bool, float]:
        now = time.monotonic()
        with self._lock:
            count, window_start = self._hits.get(key, (0, now))
            if now - window_start >= window_seconds:
                count, window_start = 0, now
            count += 1
            self._hits[key] = (count, window_start)
            retry_after = window_seconds - (now - window_start)
            return count <= limit, max(0.0, retry_after)


_store = _FixedWindow()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(bucket: str, *, limit: int, window_seconds: float = 60.0):
    """Return a dependency that enforces ``limit`` requests per window per IP."""

    async def _dependency(request: Request) -> None:
        if not _ENABLED:
            return
        ok, retry_after = _store.check((_client_ip(request), bucket), limit, window_seconds)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for '{bucket}'. Try again in {retry_after:.0f}s.",
                headers={"Retry-After": str(int(retry_after) + 1)},
            )

    return Depends(_dependency)


def reset() -> None:
    """Clear all counters (used by tests)."""

    _store._hits.clear()


# Named limits used across routes.
LOGIN_LIMIT = rate_limit("auth-login", limit=10, window_seconds=60)
REGISTER_LIMIT = rate_limit("auth-register", limit=5, window_seconds=60)
REFRESH_LIMIT = rate_limit("auth-refresh", limit=20, window_seconds=60)
ANALYSIS_RUN_LIMIT = rate_limit("analysis-run", limit=20, window_seconds=60)
AGENT_LIMIT = rate_limit("agent", limit=30, window_seconds=60)
