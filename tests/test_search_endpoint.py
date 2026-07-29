from __future__ import annotations

from fastapi.testclient import TestClient


def test_stage0_query_end_to_end(client: TestClient) -> None:
    resp = client.get(
        "/gmail/v1/users/me/messages",
        params={"q": "to:pitches@acme.example newer_than:90d"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "messages" in body
    assert "resultSizeEstimate" in body
    for item in body["messages"]:
        assert set(item.keys()) == {"id", "threadId"}


def test_search_pagination(client: TestClient) -> None:
    first = client.get(
        "/gmail/v1/users/me/messages",
        params={"q": "newer_than:90d", "maxResults": 5},
    )
    body = first.json()
    if body["resultSizeEstimate"] > 5:
        assert "nextPageToken" in body
        second = client.get(
            "/gmail/v1/users/me/messages",
            params={
                "q": "newer_than:90d",
                "maxResults": 5,
                "pageToken": body["nextPageToken"],
            },
        )
        assert second.status_code == 200
        first_ids = {m["id"] for m in body["messages"]}
        second_ids = {m["id"] for m in second.json()["messages"]}
        assert first_ids.isdisjoint(second_ids)


def test_invalid_page_token_400(client: TestClient) -> None:
    resp = client.get(
        "/gmail/v1/users/me/messages",
        params={"q": "newer_than:90d", "pageToken": "not-valid"},
    )
    assert resp.status_code == 400


def test_no_send_endpoint_exists(client: TestClient) -> None:
    # `messages/send` isn't a registered route. It collides with the
    # `GET /messages/{message_id}` path shape, so a POST there surfaces as
    # 405 (method not allowed on that path) rather than 404 — either way,
    # there is no way to actually send mail through this mock.
    resp = client.post("/gmail/v1/users/me/messages/send", json={})
    assert resp.status_code in (404, 405)
