"""mock-document-generation: realistic pdf/docx/xlsx attachment content for
this mock's pitch-inbound emails (Ticket 0008).

>>> THIS IS MOCK-ONLY, DEV-FIXTURE CODE. <<<

It has no relationship to the real Gmail API and must never be imported by
anything that talks to real Gmail. Its only job is making synthetic
attachments here look enough like a real pitch deck/cap table/memo that a
downstream document classifier has something non-trivial to summarize when
developed against this mock. Company names, financials, and all document
content are entirely fabricated (via Faker and/or `claude -p`, see
content.py) — never real deal data.

Public entry point: `generate_attachment_content`, used by
generator/pitch.py to produce the bytes behind each pitch-thread
attachment, and by server.py to read them back for
`GET .../attachments/{id}`.
"""

from __future__ import annotations

from pathlib import Path

from mock_gmail_api.docgen.cache import DocumentCache, default_cache
from mock_gmail_api.docgen.catalog import CAP_TABLE, ONE_PAGER, PITCH_DECK, DocType
from mock_gmail_api.models import PitchMeta

__all__ = [
    "CAP_TABLE",
    "ONE_PAGER",
    "PITCH_DECK",
    "DocType",
    "DocumentCache",
    "default_cache",
    "generate_attachment_content",
]


def generate_attachment_content(
    cache: DocumentCache, doc_type: DocType, meta: PitchMeta
) -> tuple[str, bytes]:
    """Returns (content_ref, bytes) for one attachment. content_ref is
    opaque — store it on the Attachment row and pass it back to
    `cache.read` to look the same bytes up later without regenerating."""
    return cache.get_or_generate(doc_type, meta)


def read_cached_content(cache_dir: str | Path, content_ref: str) -> bytes:
    return (Path(cache_dir) / content_ref).read_bytes()
