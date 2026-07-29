"""Trivial bearer-token auth. Not a real OAuth2 flow — no `/token` or
`/authorize` endpoints — this mock only exists to make callers pass *some*
credential-shaped header, the way real Gmail REST calls do.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Header, HTTPException


def make_require_bearer_token(dev_token: str | None) -> Callable[..., Awaitable[str]]:
    async def require_bearer_token(authorization: str | None = Header(default=None)) -> str:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        token = authorization[len("bearer ") :].strip()
        if not token:
            raise HTTPException(status_code=401, detail="empty bearer token")
        if dev_token is not None and token != dev_token:
            raise HTTPException(status_code=401, detail="invalid bearer token")
        return token

    return require_bearer_token
