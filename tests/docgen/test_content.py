from __future__ import annotations

import json

import pytest

from mock_gmail_api.docgen.catalog import CAP_TABLE, ONE_PAGER, PITCH_DECK
from mock_gmail_api.docgen.content import BACKEND_ENV_VAR, StubBackend, get_backend
from mock_gmail_api.models import PitchMeta

_META = PitchMeta(company_name="Acme Robotics", sector="Robotics", ask="£1.5m", stage="Seed")


def test_stub_backend_is_deterministic() -> None:
    backend = StubBackend()
    assert backend.generate(PITCH_DECK, _META) == backend.generate(PITCH_DECK, _META)


def test_stub_backend_differs_by_doc_type() -> None:
    backend = StubBackend()
    assert backend.generate(PITCH_DECK, _META) != backend.generate(ONE_PAGER, _META)


def test_stub_backend_differs_by_company() -> None:
    other = PitchMeta(
        company_name="Northwind Therapeutics", sector="Biotech", ask="£2m", stage="Seed"
    )
    backend = StubBackend()
    assert backend.generate(PITCH_DECK, _META) != backend.generate(PITCH_DECK, other)


def test_stub_backend_cap_table_is_valid_json_array_of_rows() -> None:
    backend = StubBackend()
    rows = json.loads(backend.generate(CAP_TABLE, _META))
    assert isinstance(rows, list)
    assert rows
    for row in rows:
        assert {"holder", "share_class", "shares", "ownership_pct"} <= row.keys()


def test_get_backend_stub() -> None:
    assert isinstance(get_backend("stub"), StubBackend)


def test_get_backend_reads_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(BACKEND_ENV_VAR, "stub")
    assert isinstance(get_backend(), StubBackend)


def test_get_backend_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown docgen backend"):
        get_backend("nonsense")
