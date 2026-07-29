from __future__ import annotations

from fastapi.testclient import TestClient


def test_create_draft(client: TestClient) -> None:
    resp = client.post(
        "/gmail/v1/users/me/drafts",
        json={
            "to": ["harry@acme.example"],
            "subject": "Weekly tear-sheet",
            "body_text": "See attached summary.",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["message"]["labelIds"] == ["DRAFT"]
    assert "id" in body
    assert "id" in body["message"]


def test_no_send_endpoint_under_drafts(client: TestClient) -> None:
    resp = client.post("/gmail/v1/users/me/drafts/send", json={})
    assert resp.status_code == 404
