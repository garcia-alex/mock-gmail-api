"""Pure functions turning flat SQLite-row dataclasses (models.py) into
real Gmail REST API JSON shapes. No I/O, no FastAPI — server.py is the only
caller.

PitchMeta is deliberately emitted only as the custom header
`X-Pitch-Meta` inside `payload.headers`, never as a top-level JSON
field. This is intentional domain realism: real Gmail has no such
structured field, so exposing pitch metadata as a normal top-level key
would let a real extraction pipeline shortcut past actually parsing the
body/PDF text — which is the behavior Stage-0 must exercise against this
mock.
"""

from __future__ import annotations

import base64
import json
from typing import Any

from mock_gmail_api.models import Attachment, Draft, Message, Thread


def _b64url(data: str) -> str:
    return base64.urlsafe_b64encode(data.encode("utf-8")).decode("ascii")


def _headers_list(message: Message) -> list[dict[str, str]]:
    headers = dict(message.headers)
    if message.pitch_meta is not None:
        headers["X-Pitch-Meta"] = json.dumps(
            {
                "companyName": message.pitch_meta.company_name,
                "sector": message.pitch_meta.sector,
                "ask": message.pitch_meta.ask,
                "stage": message.pitch_meta.stage,
            }
        )
    return [{"name": name, "value": value} for name, value in headers.items()]


def _attachment_part(attachment: Attachment) -> dict[str, Any]:
    return {
        "partId": attachment.id,
        "mimeType": attachment.mimetype,
        "filename": attachment.filename,
        "headers": [{"name": "Content-Type", "value": attachment.mimetype}],
        "body": {"attachmentId": attachment.id, "size": attachment.size_bytes},
    }


def _payload(message: Message, attachments: list[Attachment]) -> dict[str, Any]:
    headers = _headers_list(message)

    if message.body_html is None and not attachments:
        return {
            "mimeType": "text/plain",
            "headers": headers,
            "body": {"size": len(message.body_text), "data": _b64url(message.body_text)},
        }

    parts: list[dict[str, Any]] = [
        {
            "partId": "0",
            "mimeType": "text/plain",
            "headers": [{"name": "Content-Type", "value": "text/plain"}],
            "body": {"size": len(message.body_text), "data": _b64url(message.body_text)},
        }
    ]
    if message.body_html is not None:
        parts.append(
            {
                "partId": "1",
                "mimeType": "text/html",
                "headers": [{"name": "Content-Type", "value": "text/html"}],
                "body": {"size": len(message.body_html), "data": _b64url(message.body_html)},
            }
        )
    parts.extend(_attachment_part(attachment) for attachment in attachments)

    return {
        "mimeType": "multipart/mixed",
        "headers": headers,
        "parts": parts,
    }


def message_list_item_json(message: Message) -> dict[str, str]:
    """Real Gmail's `messages.list` only returns `{id, threadId}` per item —
    callers must `get` each one separately."""
    return {"id": message.id, "threadId": message.thread_id}


def message_full_json(message: Message, attachments: list[Attachment]) -> dict[str, Any]:
    payload = _payload(message, attachments)
    size_estimate = len(message.body_text) + sum(a.size_bytes for a in attachments)
    return {
        "id": message.id,
        "threadId": message.thread_id,
        "labelIds": message.label_ids,
        "snippet": message.body_text[:140],
        "historyId": str(message.history_id),
        "internalDate": str(message.internal_date),
        "payload": payload,
        "sizeEstimate": size_estimate,
    }


def thread_json(thread: Thread, messages: list[tuple[Message, list[Attachment]]]) -> dict[str, Any]:
    """No thread-level snippet, matching real Gmail's `threads.get` shape."""
    return {
        "id": thread.id,
        "historyId": str(thread.history_id),
        "messages": [message_full_json(message, atts) for message, atts in messages],
    }


def labels_list_json(label_ids: list[str]) -> dict[str, Any]:
    return {
        "labels": [
            {"id": label_id, "name": label_id, "type": "system" if label_id.isupper() else "user"}
            for label_id in label_ids
        ]
    }


def draft_json(draft: Draft, message: Message, attachments: list[Attachment]) -> dict[str, Any]:
    full = message_full_json(message, attachments)
    return {
        "id": draft.id,
        "message": {
            "id": full["id"],
            "threadId": full["threadId"],
            "labelIds": ["DRAFT"],
            "payload": full["payload"],
        },
    }


def attachment_json(attachment_id: str, size: int, data: str) -> dict[str, Any]:
    return {"attachmentId": attachment_id, "size": size, "data": data}
