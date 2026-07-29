"""Opaque pageToken encode/decode. Offset-based under the hood, but wrapped
as a base64 token of `offset:query_hash` so callers can't rely on token
internals — this matches real Gmail's opaque-token behavior more faithfully
than exposing a literal integer offset.
"""

from __future__ import annotations

import base64
import hashlib


def _query_hash(query: str | None) -> str:
    return hashlib.sha256((query or "").encode("utf-8")).hexdigest()[:16]


def encode_page_token(offset: int, query: str | None) -> str:
    raw = f"{offset}:{_query_hash(query)}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


class InvalidPageToken(ValueError):
    pass


def decode_page_token(token: str, query: str | None) -> int:
    """Decode a pageToken, verifying it was issued for the same query — a
    token from a different search is rejected rather than silently
    reinterpreted, since its offset would refer to a different result set.
    """
    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        offset_str, token_hash = raw.split(":", 1)
        offset = int(offset_str)
    except (ValueError, UnicodeDecodeError) as exc:
        raise InvalidPageToken(f"malformed page token: {token!r}") from exc

    if token_hash != _query_hash(query):
        raise InvalidPageToken("page token does not match the current query")

    return offset
