from __future__ import annotations

from pathlib import Path

from mock_gmail_api import db
from mock_gmail_api.docgen.cache import DocumentCache
from mock_gmail_api.docgen.content import StubBackend
from mock_gmail_api.generator.seed import GenerateConfig, generate


def _stub_config(tmp_path: Path, cache_name: str, seed: int, volume: int) -> GenerateConfig:
    docgen_cache = DocumentCache(cache_dir=tmp_path / cache_name, backend=StubBackend())
    return GenerateConfig(seed=seed, volume=volume, docgen_cache=docgen_cache)


def _dump(db_path: Path) -> list[tuple[object, ...]]:
    conn = db.connect(db_path)
    rows = conn.execute("SELECT * FROM messages ORDER BY id").fetchall()
    dumped = [tuple(row) for row in rows]
    conn.close()
    return dumped


def _dump_attachments(db_path: Path) -> list[tuple[object, ...]]:
    conn = db.connect(db_path)
    rows = conn.execute(
        "SELECT filename, mimetype, size_bytes, content_ref FROM attachments ORDER BY id"
    ).fetchall()
    dumped = [tuple(row) for row in rows]
    conn.close()
    return dumped


def test_same_seed_is_byte_identical(tmp_path: Path) -> None:
    db_a = tmp_path / "a.sqlite"
    db_b = tmp_path / "b.sqlite"

    generate(_stub_config(tmp_path, "cache_a", seed=42, volume=50), db_a)
    generate(_stub_config(tmp_path, "cache_b", seed=42, volume=50), db_b)

    assert _dump(db_a) == _dump(db_b)
    assert _dump_attachments(db_a) == _dump_attachments(db_b)


def test_different_seed_differs(tmp_path: Path) -> None:
    db_a = tmp_path / "a.sqlite"
    db_b = tmp_path / "c.sqlite"

    generate(_stub_config(tmp_path, "cache_a", seed=42, volume=50), db_a)
    generate(_stub_config(tmp_path, "cache_b", seed=7, volume=50), db_b)

    assert _dump(db_a) != _dump(db_b)


def test_generate_if_missing_skips_existing(tmp_path: Path) -> None:
    from mock_gmail_api.generator.seed import generate_if_missing

    db_path = tmp_path / "fixtures.sqlite"
    ran_first = generate_if_missing(_stub_config(tmp_path, "cache", seed=1, volume=5), db_path)
    mtime_after_first = db_path.stat().st_mtime_ns

    ran_second = generate_if_missing(_stub_config(tmp_path, "cache", seed=99, volume=5), db_path)
    mtime_after_second = db_path.stat().st_mtime_ns

    assert ran_first is True
    assert ran_second is False
    assert mtime_after_first == mtime_after_second
