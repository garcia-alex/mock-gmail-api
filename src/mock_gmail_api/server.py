"""Mock Gmail REST API server. Routes mirror real Gmail's
`/gmail/v1/users/me/...` paths and JSON shapes for the narrow subset this
mock implements: messages.list (search), messages.get, threads.get,
labels.list, drafts.create, messages.attachments.get. No modify/labels-write,
no history/watch/push, no settings, and never `messages.send` — see the
README's Scope/Non-goals.

Route handlers stay thin: parsing/validation lives in query.py, storage in
db.py, JSON shaping in gmail_json.py, fault injection in faults.py. The DB
connection is injected via `Depends`, not a module global, so tests get
isolated tmp DBs per app instance.
"""

import base64
import sqlite3
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Any

import faker
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from mock_gmail_api import db, gmail_json
from mock_gmail_api.auth import make_require_bearer_token
from mock_gmail_api.docgen.cache import default_cache_dir
from mock_gmail_api.faults import FaultProfile, apply_http
from mock_gmail_api.generator import new_id
from mock_gmail_api.models import Draft, Message, Thread
from mock_gmail_api.pagination import InvalidPageToken, decode_page_token, encode_page_token
from mock_gmail_api.query import parse_query

DEFAULT_PAGE_SIZE = 20


class DraftCreateRequest(BaseModel):
    """Simplified draft-create body — not the real API's strict RFC822
    `raw` field. See README for the documented divergence."""

    to: list[str]
    subject: str
    body_text: str
    body_html: str | None = None
    thread_id: str | None = None


def _parse_fault_header(value: str | None) -> list[str] | None:
    if value is None:
        return None
    if value.strip().lower() in ("", "none"):
        return []
    return [name.strip() for name in value.split(",") if name.strip()]


def build_app(
    db_path: str | Path,
    fault_profile: FaultProfile | None = None,
    dev_token: str | None = None,
    docgen_cache_dir: str | Path | None = None,
) -> FastAPI:
    faults = fault_profile if fault_profile is not None else FaultProfile.none()
    cache_dir = Path(docgen_cache_dir) if docgen_cache_dir is not None else default_cache_dir()
    require_bearer_token = make_require_bearer_token(dev_token)

    app = FastAPI(title="mock-gmail-api")

    def get_conn() -> Iterator[sqlite3.Connection]:
        conn = db.connect(db_path)
        db.init_schema(conn)
        try:
            yield conn
        finally:
            conn.close()

    def _faulted(
        response: dict[str, Any],
        mock_faults: str | None,
        mock_fault_chance: str | None,
    ) -> dict[str, Any]:
        override_faults = _parse_fault_header(mock_faults)
        override_chance = float(mock_fault_chance) if mock_fault_chance is not None else None
        return apply_http(faults, response, override_faults, override_chance)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/gmail/v1/users/me/messages")
    def list_messages(
        conn: Annotated[sqlite3.Connection, Depends(get_conn)],
        _auth: Annotated[str, Depends(require_bearer_token)],
        q: str | None = None,
        pageToken: str | None = None,
        maxResults: int = DEFAULT_PAGE_SIZE,
        x_mock_faults: Annotated[str | None, Header()] = None,
        x_mock_fault_chance: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        parsed = parse_query(q)
        offset = 0
        if pageToken:
            try:
                offset = decode_page_token(pageToken, q)
            except InvalidPageToken as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        messages, total = db.search_messages(conn, parsed, limit=maxResults, offset=offset)
        next_offset = offset + maxResults
        response: dict[str, Any] = {
            "messages": [gmail_json.message_list_item_json(m) for m in messages],
            "resultSizeEstimate": total,
        }
        if next_offset < total:
            response["nextPageToken"] = encode_page_token(next_offset, q)
        return _faulted(response, x_mock_faults, x_mock_fault_chance)

    @app.get("/gmail/v1/users/me/messages/{message_id}")
    def get_message(
        message_id: str,
        conn: Annotated[sqlite3.Connection, Depends(get_conn)],
        _auth: Annotated[str, Depends(require_bearer_token)],
        x_mock_faults: Annotated[str | None, Header()] = None,
        x_mock_fault_chance: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        message = db.get_message(conn, message_id)
        if message is None:
            raise HTTPException(status_code=404, detail=f"message not found: {message_id}")
        attachments = db.list_message_attachments(conn, message_id)
        response = gmail_json.message_full_json(message, attachments)
        return _faulted(response, x_mock_faults, x_mock_fault_chance)

    @app.get("/gmail/v1/users/me/threads/{thread_id}")
    def get_thread(
        thread_id: str,
        conn: Annotated[sqlite3.Connection, Depends(get_conn)],
        _auth: Annotated[str, Depends(require_bearer_token)],
        x_mock_faults: Annotated[str | None, Header()] = None,
        x_mock_fault_chance: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        thread = db.get_thread(conn, thread_id)
        if thread is None:
            raise HTTPException(status_code=404, detail=f"thread not found: {thread_id}")
        messages = db.list_thread_messages(conn, thread_id)
        pairs = [(m, db.list_message_attachments(conn, m.id)) for m in messages]
        response = gmail_json.thread_json(thread, pairs)
        return _faulted(response, x_mock_faults, x_mock_fault_chance)

    @app.get("/gmail/v1/users/me/labels")
    def list_labels(
        conn: Annotated[sqlite3.Connection, Depends(get_conn)],
        _auth: Annotated[str, Depends(require_bearer_token)],
        x_mock_faults: Annotated[str | None, Header()] = None,
        x_mock_fault_chance: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        response = gmail_json.labels_list_json(db.list_labels(conn))
        return _faulted(response, x_mock_faults, x_mock_fault_chance)

    @app.post("/gmail/v1/users/me/drafts")
    def create_draft(
        request: DraftCreateRequest,
        conn: Annotated[sqlite3.Connection, Depends(get_conn)],
        _auth: Annotated[str, Depends(require_bearer_token)],
        x_mock_faults: Annotated[str | None, Header()] = None,
        x_mock_fault_chance: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        fake = faker.Faker()
        message_id = new_id(fake, "msg")
        thread_id = request.thread_id or new_id(fake, "thr")
        now_ms = int(time.time() * 1000)

        message = Message(
            id=message_id,
            thread_id=thread_id,
            from_addr="me",
            to_addrs=request.to,
            subject=request.subject,
            body_text=request.body_text,
            body_html=request.body_html,
            headers={
                "To": ", ".join(request.to),
                "Subject": request.subject,
            },
            internal_date=now_ms,
            label_ids=["DRAFT"],
        )
        if db.get_thread(conn, thread_id) is None:
            db.insert_thread(
                conn, Thread(id=thread_id, subject=request.subject, label_ids=["DRAFT"])
            )
        db.insert_message(conn, message)
        draft = Draft(
            id=new_id(fake, "drf"),
            message_id=message_id,
            thread_id=thread_id,
            created_at=now_ms,
        )
        db.insert_draft(conn, draft)
        conn.commit()

        response = gmail_json.draft_json(draft, message, [])
        return _faulted(response, x_mock_faults, x_mock_fault_chance)

    @app.get("/gmail/v1/users/me/messages/{message_id}/attachments/{attachment_id}")
    def get_attachment(
        message_id: str,
        attachment_id: str,
        conn: Annotated[sqlite3.Connection, Depends(get_conn)],
        _auth: Annotated[str, Depends(require_bearer_token)],
        x_mock_faults: Annotated[str | None, Header()] = None,
        x_mock_fault_chance: Annotated[str | None, Header()] = None,
    ) -> dict[str, Any]:
        attachment = db.get_attachment(conn, message_id, attachment_id)
        if attachment is None:
            raise HTTPException(status_code=404, detail=f"attachment not found: {attachment_id}")
        if attachment.content_ref is not None:
            # Real generated pdf/docx/xlsx content — see mock_gmail_api.docgen.
            raw = (cache_dir / attachment.content_ref).read_bytes()
        else:
            # No generated content for this attachment (shouldn't happen for
            # anything the current generator produces) — fall back to filler
            # bytes so the endpoint still returns something size-consistent.
            raw = (b"MOCKATTACHMENTDATA" * (attachment.size_bytes // 18 + 1))[
                : attachment.size_bytes
            ]
        data = base64.urlsafe_b64encode(raw).decode("ascii")
        response = gmail_json.attachment_json(attachment.id, len(raw), data)
        return _faulted(response, x_mock_faults, x_mock_fault_chance)

    return app
