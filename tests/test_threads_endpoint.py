from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_thread_returns_full_messages(client: TestClient) -> None:
    search = client.get("/gmail/v1/users/me/messages", params={"maxResults": 1})
    message_id = search.json()["messages"][0]["id"]
    message = client.get(f"/gmail/v1/users/me/messages/{message_id}").json()
    thread_id = message["threadId"]

    resp = client.get(f"/gmail/v1/users/me/threads/{thread_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == thread_id
    assert "snippet" not in body
    assert len(body["messages"]) >= 1
    for msg in body["messages"]:
        assert "payload" in msg


def test_get_thread_404(client: TestClient) -> None:
    resp = client.get("/gmail/v1/users/me/threads/thr_does_not_exist")
    assert resp.status_code == 404


def test_get_message_404(client: TestClient) -> None:
    resp = client.get("/gmail/v1/users/me/messages/msg_does_not_exist")
    assert resp.status_code == 404


def test_get_message_full_shape(client: TestClient) -> None:
    search = client.get("/gmail/v1/users/me/messages", params={"maxResults": 1})
    message_id = search.json()["messages"][0]["id"]
    resp = client.get(f"/gmail/v1/users/me/messages/{message_id}")
    body = resp.json()
    assert body["id"] == message_id
    assert "payload" in body
    assert "headers" in body["payload"]
    assert "sizeEstimate" in body
