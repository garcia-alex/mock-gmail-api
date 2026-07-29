from __future__ import annotations

from pathlib import Path

from mock_gmail_api.docgen.cache import DocumentCache, cache_key
from mock_gmail_api.docgen.catalog import CAP_TABLE, ONE_PAGER, PITCH_DECK
from mock_gmail_api.docgen.content import ContentBackend
from mock_gmail_api.models import PitchMeta

_META = PitchMeta(company_name="Acme Robotics", sector="Robotics", ask="£1.5m", stage="Seed")


class _CountingBackend:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, doc_type: object, meta: object) -> str:
        self.calls += 1
        if getattr(doc_type, "key", None) == "cap_table":
            return (
                '[{"holder": "Jane Doe", "share_class": "Common", '
                '"shares": 100, "ownership_pct": 10.0}]'
            )
        return "## Overview\n- one\n- two\n"


def _cache(tmp_path: Path, backend: ContentBackend) -> DocumentCache:
    return DocumentCache(cache_dir=tmp_path / "cache", backend=backend)


def test_get_or_generate_calls_backend_once_per_cache_key(tmp_path: Path) -> None:
    backend = _CountingBackend()
    cache = _cache(tmp_path, backend)  # type: ignore[arg-type]

    ref1, data1 = cache.get_or_generate(PITCH_DECK, _META)
    ref2, data2 = cache.get_or_generate(PITCH_DECK, _META)

    assert backend.calls == 1
    assert ref1 == ref2
    assert data1 == data2


def test_different_doc_types_get_different_cache_entries(tmp_path: Path) -> None:
    backend = _CountingBackend()
    cache = _cache(tmp_path, backend)  # type: ignore[arg-type]

    pitch_ref, _ = cache.get_or_generate(PITCH_DECK, _META)
    one_pager_ref, _ = cache.get_or_generate(ONE_PAGER, _META)
    cap_table_ref, _ = cache.get_or_generate(CAP_TABLE, _META)

    assert backend.calls == 3
    assert len({pitch_ref, one_pager_ref, cap_table_ref}) == 3


def test_different_companies_get_different_cache_entries() -> None:
    other = PitchMeta(
        company_name="Northwind Therapeutics", sector="Biotech", ask="£2m", stage="Seed"
    )
    assert cache_key(PITCH_DECK, _META) != cache_key(PITCH_DECK, other)


def test_cache_persists_across_separate_cache_instances(tmp_path: Path) -> None:
    backend = _CountingBackend()
    cache_dir = tmp_path / "cache"

    DocumentCache(cache_dir=cache_dir, backend=backend).get_or_generate(PITCH_DECK, _META)  # type: ignore[arg-type]
    second_backend = _CountingBackend()
    ref, data = DocumentCache(cache_dir=cache_dir, backend=second_backend).get_or_generate(  # type: ignore[arg-type]
        PITCH_DECK, _META
    )

    assert second_backend.calls == 0
    assert data
    assert (cache_dir / ref).exists()
