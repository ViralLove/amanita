"""
Optional Bearer guard for Custom GPT Actions → /activities and /reference.

If GPT_ACTIONS_BEARER_SECRET is unset or empty, middleware is a no-op (backward compatible).
If set, requests under protected prefixes must send Authorization: Bearer <exact secret>.
Uses timing-safe comparison. Does not replace HMAC skip — runs inside stack after HMAC passes through.
"""

from __future__ import annotations

import logging
import secrets
import time
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("amanita_api.gpt_actions_bearer")

# Prefixes aligned with task GIM-BCK-0 / api.md
_PROTECTED_PREFIXES = ("/activities", "/reference")


def _parse_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:].strip() or None


class GptActionsBearerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, bearer_secret: str):
        super().__init__(app)
        self._secret = (bearer_secret or "").strip()

    async def dispatch(self, request: Request, call_next):
        if not self._secret:
            return await call_next(request)

        path = request.url.path
        if not any(path == p or path.startswith(p + "/") for p in _PROTECTED_PREFIXES):
            return await call_next(request)

        token = _parse_bearer(request.headers.get("Authorization"))
        if token is None:
            return _unauthorized(request.url.path, "missing_bearer")
        a, b = token.encode("utf-8"), self._secret.encode("utf-8")
        if len(a) != len(b) or not secrets.compare_digest(a, b):
            return _unauthorized(request.url.path, "invalid_bearer")

        return await call_next(request)


def _unauthorized(path: str, code: str) -> JSONResponse:
    return JSONResponse(
        status_code=401,
        content={
            "success": False,
            "error": "gpt_actions_auth_error",
            "error_code": code,
            "message": "Authorization Bearer required for this path",
            "timestamp": int(time.time()),
            "path": path,
        },
    )
