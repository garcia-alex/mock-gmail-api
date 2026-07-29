"""SQLite storage layer for the mock fixture database.

Storage is flat/relational; Gmail-API-shaped JSON is assembled by
gmail_json.py, not here. Single-inbox scope: no `mailboxes` table, since
real Gmail's REST API has no such concept either — every row belongs to the
one `users/me` account this server represents.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from mock_gmail_api.models import Attachment, Draft, Message, PitchMeta, Thread
from mock_gmail_api.query import ParsedQuery

SCHEMA = """
CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    label_ids TEXT NOT NULL,
    history_id INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL REFERENCES threads(id),
    from_addr TEXT NOT NULL,
    to_addrs TEXT NOT NULL,
    subject TEXT NOT NULL,
    body_text TEXT NOT NULL,
    body_html TEXT,
    headers_json TEXT NOT NULL,
    internal_date INTEGER NOT NULL,
    label_ids TEXT NOT NULL,
    history_id INTEGER NOT NULL DEFAULT 0,
    pitch_meta_json TEXT
);

CREATE TABLE IF NOT EXISTS attachments (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id),
    filename TEXT NOT NULL,
    mimetype TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    page_count INTEGER,
    content_ref TEXT
);

CREATE TABLE IF NOT EXISTS drafts (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL REFERENCES messages(id),
    thread_id TEXT NOT NULL REFERENCES threads(id),
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_internal_date ON messages(internal_date);
CREATE INDEX IF NOT EXISTS idx_attachments_message ON attachments(message_id);
"""

# Fixed system labels Gmail always exposes via labels.list, regardless of
# whether any message currently carries them.
SYSTEM_LABELS = [
    "INBOX",
    "UNREAD",
    "SENT",
    "DRAFT",
    "SPAM",
    "TRASH",
    "IMPORTANT",
    "STARRED",
    "CATEGORY_PERSONAL",
    "CATEGORY_SOCIAL",
    "CATEGORY_PROMOTIONS",
    "CATEGORY_UPDATES",
    "CATEGORY_FORUMS",
]


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


def reset_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        DROP TABLE IF EXISTS drafts;
        DROP TABLE IF EXISTS attachments;
        DROP TABLE IF EXISTS messages;
        DROP TABLE IF EXISTS threads;
    """)
    conn.commit()
    init_schema(conn)


def insert_thread(conn: sqlite3.Connection, thread: Thread) -> None:
    conn.execute(
        "INSERT INTO threads (id, subject, label_ids, history_id) VALUES (?, ?, ?, ?)",
        (thread.id, thread.subject, json.dumps(thread.label_ids), thread.history_id),
    )


def insert_message(conn: sqlite3.Connection, message: Message) -> None:
    pitch_json = None
    if message.pitch_meta is not None:
        pitch_json = json.dumps(
            {
                "company_name": message.pitch_meta.company_name,
                "sector": message.pitch_meta.sector,
                "ask": message.pitch_meta.ask,
                "stage": message.pitch_meta.stage,
            }
        )
    conn.execute(
        """
        INSERT INTO messages (
            id, thread_id, from_addr, to_addrs, subject,
            body_text, body_html, headers_json, internal_date, label_ids,
            history_id, pitch_meta_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            message.id,
            message.thread_id,
            message.from_addr,
            json.dumps(message.to_addrs),
            message.subject,
            message.body_text,
            message.body_html,
            json.dumps(message.headers),
            message.internal_date,
            json.dumps(message.label_ids),
            message.history_id,
            pitch_json,
        ),
    )


def insert_attachment(conn: sqlite3.Connection, attachment: Attachment) -> None:
    conn.execute(
        """
        INSERT INTO attachments (
            id, message_id, filename, mimetype, size_bytes, page_count, content_ref
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            attachment.id,
            attachment.message_id,
            attachment.filename,
            attachment.mimetype,
            attachment.size_bytes,
            attachment.page_count,
            attachment.content_ref,
        ),
    )


def insert_draft(conn: sqlite3.Connection, draft: Draft) -> None:
    conn.execute(
        "INSERT INTO drafts (id, message_id, thread_id, created_at) VALUES (?, ?, ?, ?)",
        (draft.id, draft.message_id, draft.thread_id, draft.created_at),
    )


def _row_to_thread(row: sqlite3.Row) -> Thread:
    return Thread(
        id=row["id"],
        subject=row["subject"],
        label_ids=json.loads(row["label_ids"]),
        history_id=row["history_id"],
    )


def _row_to_message(row: sqlite3.Row) -> Message:
    pitch_meta = None
    if row["pitch_meta_json"] is not None:
        raw = json.loads(row["pitch_meta_json"])
        pitch_meta = PitchMeta(
            company_name=raw["company_name"],
            sector=raw["sector"],
            ask=raw["ask"],
            stage=raw["stage"],
        )
    return Message(
        id=row["id"],
        thread_id=row["thread_id"],
        from_addr=row["from_addr"],
        to_addrs=json.loads(row["to_addrs"]),
        subject=row["subject"],
        body_text=row["body_text"],
        body_html=row["body_html"],
        headers=json.loads(row["headers_json"]),
        internal_date=row["internal_date"],
        label_ids=json.loads(row["label_ids"]),
        history_id=row["history_id"],
        pitch_meta=pitch_meta,
    )


def _row_to_attachment(row: sqlite3.Row) -> Attachment:
    return Attachment(
        id=row["id"],
        message_id=row["message_id"],
        filename=row["filename"],
        mimetype=row["mimetype"],
        size_bytes=row["size_bytes"],
        page_count=row["page_count"],
        content_ref=row["content_ref"],
    )


def _row_to_draft(row: sqlite3.Row) -> Draft:
    return Draft(
        id=row["id"],
        message_id=row["message_id"],
        thread_id=row["thread_id"],
        created_at=row["created_at"],
    )


def list_labels(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT label_ids FROM messages").fetchall()
    labels: set[str] = set(SYSTEM_LABELS)
    for row in rows:
        labels.update(json.loads(row["label_ids"]))
    return sorted(labels)


def get_thread(conn: sqlite3.Connection, thread_id: str) -> Thread | None:
    row = conn.execute("SELECT * FROM threads WHERE id = ?", (thread_id,)).fetchone()
    return _row_to_thread(row) if row else None


def list_thread_messages(conn: sqlite3.Connection, thread_id: str) -> list[Message]:
    rows = conn.execute(
        "SELECT * FROM messages WHERE thread_id = ? ORDER BY internal_date ASC", (thread_id,)
    ).fetchall()
    return [_row_to_message(row) for row in rows]


def get_message(conn: sqlite3.Connection, message_id: str) -> Message | None:
    row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
    return _row_to_message(row) if row else None


def list_message_attachments(conn: sqlite3.Connection, message_id: str) -> list[Attachment]:
    rows = conn.execute(
        "SELECT * FROM attachments WHERE message_id = ? ORDER BY id", (message_id,)
    ).fetchall()
    return [_row_to_attachment(row) for row in rows]


def get_attachment(
    conn: sqlite3.Connection, message_id: str, attachment_id: str
) -> Attachment | None:
    row = conn.execute(
        "SELECT * FROM attachments WHERE message_id = ? AND id = ?",
        (message_id, attachment_id),
    ).fetchone()
    return _row_to_attachment(row) if row else None


def get_draft(conn: sqlite3.Connection, draft_id: str) -> Draft | None:
    row = conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
    return _row_to_draft(row) if row else None


def search_messages(
    conn: sqlite3.Connection,
    parsed: ParsedQuery,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[Message], int]:
    """Search messages against a pre-parsed query (see query.py). Returns
    (page, total_count) so callers can build `resultSizeEstimate` and decide
    whether a `nextPageToken` is needed.
    """
    clauses: list[str] = []
    params: list[object] = []

    for term in parsed.free_terms:
        clauses.append("(subject LIKE ? OR from_addr LIKE ? OR body_text LIKE ?)")
        like = f"%{term}%"
        params.extend([like, like, like])

    if parsed.to:
        clauses.append("to_addrs LIKE ?")
        params.append(f"%{parsed.to}%")
    if parsed.from_:
        clauses.append("from_addr LIKE ?")
        params.append(f"%{parsed.from_}%")
    if parsed.subject:
        clauses.append("subject LIKE ?")
        params.append(f"%{parsed.subject}%")
    if parsed.newer_than_days is not None:
        cutoff = datetime.now(UTC) - timedelta(days=parsed.newer_than_days)
        clauses.append("internal_date >= ?")
        params.append(int(cutoff.timestamp() * 1000))
    if parsed.older_than_days is not None:
        cutoff = datetime.now(UTC) - timedelta(days=parsed.older_than_days)
        clauses.append("internal_date < ?")
        params.append(int(cutoff.timestamp() * 1000))

    where = " AND ".join(clauses) if clauses else "1 = 1"

    all_rows = conn.execute(
        f"SELECT * FROM messages WHERE {where} ORDER BY internal_date DESC", params
    ).fetchall()

    if parsed.labels:
        all_rows = [row for row in all_rows if parsed.labels & set(json.loads(row["label_ids"]))]

    if parsed.has_attachment:
        ids_with_attachments = {
            row["message_id"]
            for row in conn.execute("SELECT DISTINCT message_id FROM attachments").fetchall()
        }
        all_rows = [row for row in all_rows if row["id"] in ids_with_attachments]

    total = len(all_rows)
    page_rows = all_rows[offset : offset + limit]
    return [_row_to_message(row) for row in page_rows], total
