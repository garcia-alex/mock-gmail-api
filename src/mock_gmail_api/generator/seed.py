"""Top-level orchestration: seed a Faker instance and fill the single
`users/me` inbox with a deterministic mix of pitch-inbound and filler mail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from faker import Faker

from mock_gmail_api import db
from mock_gmail_api.docgen import DocumentCache, default_cache
from mock_gmail_api.generator.filler import make_filler_thread
from mock_gmail_api.generator.pitch import make_pitch_thread

# The target inbox the Stage-0 skill this mock was built for searches
# (`to:pitches@acme.example newer_than:1d`). Fixed rather than varying per
# run since nothing here talks to a real mailbox — using a fixed address
# lets the exact Stage-0 query be exercised end-to-end against this mock.
PITCH_INBOX_EMAIL = "pitches@acme.example"

# Fixed anchor for "now" — synthetic message dates are computed relative to
# this rather than wall-clock time, so the same seed always reproduces a
# byte-identical database regardless of when `generate` is actually run.
_DEFAULT_REFERENCE_TIME = datetime(2026, 7, 25, 12, 0, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class GenerateConfig:
    seed: int
    volume: int = 200
    pitch_ratio: float = 0.3
    reference_time: datetime = field(default=_DEFAULT_REFERENCE_TIME)
    # None means "build one from MOCK_GMAIL_DOCGEN_BACKEND/_CACHE_DIR" — see
    # docgen/cache.py. Callers that want deterministic, network-free runs
    # (e.g. tests) should pass an explicit DocumentCache with a stub backend.
    docgen_cache: DocumentCache | None = None


def generate(config: GenerateConfig, db_path: str | Path) -> None:
    fake = Faker()
    fake.seed_instance(config.seed)

    docgen_cache = config.docgen_cache if config.docgen_cache is not None else default_cache()

    conn = db.connect(db_path)
    db.reset_schema(conn)

    for _ in range(config.volume):
        if fake.random.random() < config.pitch_ratio:
            thread, messages, attachments = make_pitch_thread(
                fake, PITCH_INBOX_EMAIL, config.reference_time, docgen_cache
            )
            db.insert_thread(conn, thread)
            for message in messages:
                db.insert_message(conn, message)
            for attachment in attachments:
                db.insert_attachment(conn, attachment)
        else:
            thread, messages = make_filler_thread(fake, PITCH_INBOX_EMAIL, config.reference_time)
            db.insert_thread(conn, thread)
            for message in messages:
                db.insert_message(conn, message)

    conn.commit()
    conn.close()


def generate_if_missing(config: GenerateConfig, db_path: str | Path) -> bool:
    """Skip regeneration if the DB file already exists, so a mounted Docker
    volume persists across container restarts. Returns True if generation
    ran.
    """
    if Path(db_path).exists():
        return False
    generate(config, db_path)
    return True
