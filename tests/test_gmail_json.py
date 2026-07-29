from __future__ import annotations

import base64

from mock_gmail_api.gmail_json import (
    attachment_json,
    labels_list_json,
    message_full_json,
    message_list_item_json,
    thread_json,
)
from mock_gmail_api.models import Attachment, Message, PitchMeta, Thread

_MSG_PLAIN = Message(
    id="msg_1",
    thread_id="thr_1",
    from_addr="founder@acme.com",
    to_addrs=["pitches@acme.example"],
    subject="Acme pitch",
    body_text="Hello world",
    body_html=None,
    headers={"From": "founder@acme.com", "To": "pitches@acme.example", "Subject": "Acme pitch"},
    internal_date=1234567890000,
    label_ids=["INBOX", "UNREAD"],
    history_id=1,
    pitch_meta=PitchMeta(company_name="Acme", sector="SaaS", ask="£1m", stage="Seed"),
)

_ATTACHMENT = Attachment(
    id="att_1",
    message_id="msg_1",
    filename="Acme_Deck.pdf",
    mimetype="application/pdf",
    size_bytes=1234,
    page_count=12,
)


def test_message_full_json_plain_body_roundtrip() -> None:
    result = message_full_json(_MSG_PLAIN, [])
    assert result["id"] == "msg_1"
    assert result["threadId"] == "thr_1"
    data = result["payload"]["body"]["data"]
    decoded = base64.urlsafe_b64decode(data.encode("ascii")).decode("utf-8")
    assert decoded == "Hello world"


def test_pitch_meta_only_in_header_not_top_level() -> None:
    result = message_full_json(_MSG_PLAIN, [])
    assert "pitchMeta" not in result
    header_names = {h["name"] for h in result["payload"]["headers"]}
    assert "X-Pitch-Meta" in header_names
    pitch_header = next(
        h["value"] for h in result["payload"]["headers"] if h["name"] == "X-Pitch-Meta"
    )
    assert "Acme" in pitch_header


def test_attachment_parts_carry_no_inline_data() -> None:
    result = message_full_json(_MSG_PLAIN, [_ATTACHMENT])
    parts = result["payload"]["parts"]
    attachment_parts = [p for p in parts if p.get("filename") == "Acme_Deck.pdf"]
    assert len(attachment_parts) == 1
    body = attachment_parts[0]["body"]
    assert body["attachmentId"] == "att_1"
    assert body["size"] == 1234
    assert "data" not in body


def test_html_alt_part_present_when_body_html_set() -> None:
    msg = Message(
        id="msg_2",
        thread_id="thr_1",
        from_addr="a@b.com",
        to_addrs=["pitches@acme.example"],
        subject="s",
        body_text="text",
        body_html="<p>text</p>",
        headers={},
        internal_date=1,
        label_ids=[],
        history_id=0,
    )
    result = message_full_json(msg, [])
    mime_types = {p["mimeType"] for p in result["payload"]["parts"]}
    assert "text/plain" in mime_types
    assert "text/html" in mime_types


def test_message_list_item_is_id_and_thread_id_only() -> None:
    item = message_list_item_json(_MSG_PLAIN)
    assert item == {"id": "msg_1", "threadId": "thr_1"}


def test_thread_json_no_top_level_snippet() -> None:
    thread = Thread(id="thr_1", subject="Acme pitch", label_ids=["INBOX"], history_id=1)
    result = thread_json(thread, [(_MSG_PLAIN, [])])
    assert "snippet" not in result
    assert result["id"] == "thr_1"
    assert len(result["messages"]) == 1


def test_labels_list_includes_system_and_user_labels() -> None:
    result = labels_list_json(["INBOX", "UNREAD", "PITCH-INBOUND"])
    ids = {label["id"] for label in result["labels"]}
    assert ids == {"INBOX", "UNREAD", "PITCH-INBOUND"}


def test_attachment_json_shape() -> None:
    result = attachment_json("att_1", 1234, "ZmFrZQ==")
    assert result == {"attachmentId": "att_1", "size": 1234, "data": "ZmFrZQ=="}
