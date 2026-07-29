from __future__ import annotations

import pytest

from mock_gmail_api.pagination import InvalidPageToken, decode_page_token, encode_page_token


def test_roundtrip() -> None:
    token = encode_page_token(20, "to:pitches@acme.example")
    assert decode_page_token(token, "to:pitches@acme.example") == 20


def test_token_is_opaque_not_a_raw_integer() -> None:
    token = encode_page_token(20, "q")
    assert token != "20"


def test_mismatched_query_rejected() -> None:
    token = encode_page_token(20, "q1")
    with pytest.raises(InvalidPageToken):
        decode_page_token(token, "q2")


def test_malformed_token_rejected() -> None:
    with pytest.raises(InvalidPageToken):
        decode_page_token("not-a-valid-token!!", "q")


def test_paging_through_results_has_no_gaps_or_overlaps() -> None:
    total_items = list(range(55))
    page_size = 20
    query = "newer_than:30d"

    seen: list[int] = []
    offset = 0
    token: str | None = None
    while True:
        if token is not None:
            offset = decode_page_token(token, query)
        page = total_items[offset : offset + page_size]
        seen.extend(page)
        next_offset = offset + page_size
        if next_offset >= len(total_items):
            break
        token = encode_page_token(next_offset, query)

    assert seen == total_items
