from __future__ import annotations

import base64

from fastapi.testclient import TestClient

_PITCH_META = {
    "company_name": "Admin Test Co",
    "sector": "Fintech",
    "ask": "£1.2m",
    "stage": "Seed",
}


def test_create_admin_message_is_retrievable(client: TestClient) -> None:
    resp = client.post(
        "/admin/messages",
        json={
            "subject": "Admin Test Co — Seed pitch",
            "body_text": "Hi, we're raising a seed round.",
            "from_addr": "founder@admintestco.example",
        },
    )
    assert resp.status_code == 200
    created = resp.json()
    message_id = created["id"]

    fetched = client.get(f"/gmail/v1/users/me/messages/{message_id}").json()
    assert fetched["id"] == message_id
    assert fetched["payload"]["headers"] == created["payload"]["headers"]

    listed = client.get(
        "/gmail/v1/users/me/messages", params={"q": "from:founder@admintestco.example"}
    ).json()
    assert any(m["id"] == message_id for m in listed["messages"])


def test_create_admin_message_does_not_disturb_existing_messages(client: TestClient) -> None:
    existing = client.get("/gmail/v1/users/me/messages", params={"maxResults": 1}).json()
    existing_id = existing["messages"][0]["id"]
    before = client.get(f"/gmail/v1/users/me/messages/{existing_id}").json()

    client.post(
        "/admin/messages",
        json={
            "subject": "Unrelated Co — Series A pitch",
            "body_text": "New pitch content.",
            "from_addr": "founder@unrelatedco.example",
        },
    )

    after = client.get(f"/gmail/v1/users/me/messages/{existing_id}").json()
    assert after == before


def test_create_admin_message_is_append_only_not_idempotent(client: TestClient) -> None:
    """Repeated identical calls each create a new, independently retrievable
    message — mirroring mock-granola-api's /admin/notes."""
    payload = {
        "subject": "Repeat Co — Seed pitch",
        "body_text": "Same content every time.",
        "from_addr": "founder@repeatco.example",
    }
    first = client.post("/admin/messages", json=payload).json()
    second = client.post("/admin/messages", json=payload).json()

    assert first["id"] != second["id"]
    for message_id in (first["id"], second["id"]):
        assert client.get(f"/gmail/v1/users/me/messages/{message_id}").status_code == 200


def test_create_admin_message_with_pitch_meta_sets_pitch_label(client: TestClient) -> None:
    resp = client.post(
        "/admin/messages",
        json={
            "subject": "Admin Test Co — Seed pitch",
            "body_text": "Pitch body.",
            "from_addr": "founder@admintestco.example",
            "pitch_meta": _PITCH_META,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "PITCH-INBOUND" in body["labelIds"]
    header_names = {h["name"] for h in body["payload"]["headers"]}
    assert "X-Pitch-Meta" in header_names


def test_create_admin_message_with_attachment_spec_generates_real_attachment(
    client: TestClient,
) -> None:
    resp = client.post(
        "/admin/messages",
        json={
            "subject": "Admin Test Co — Seed pitch",
            "body_text": "Pitch body with deck attached.",
            "from_addr": "founder@admintestco.example",
            "pitch_meta": _PITCH_META,
            "attachments": [{"doc_type": "pitch_deck"}],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    parts = body["payload"]["parts"]
    attachment_part = next(p for p in parts if "attachmentId" in p.get("body", {}))
    assert attachment_part["mimeType"] == "application/pdf"

    message_id = body["id"]
    attachment_id = attachment_part["body"]["attachmentId"]
    attachment_resp = client.get(
        f"/gmail/v1/users/me/messages/{message_id}/attachments/{attachment_id}"
    )
    assert attachment_resp.status_code == 200
    raw = base64.urlsafe_b64decode(attachment_resp.json()["data"].encode("ascii"))
    assert raw.startswith(b"%PDF-")


def test_create_admin_message_attachment_without_pitch_meta_is_rejected(
    client: TestClient,
) -> None:
    resp = client.post(
        "/admin/messages",
        json={
            "subject": "No Meta Co — pitch",
            "body_text": "Missing pitch_meta.",
            "from_addr": "founder@nometaco.example",
            "attachments": [{"doc_type": "pitch_deck"}],
        },
    )
    assert resp.status_code == 400
