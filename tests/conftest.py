from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from mock_gmail_api.docgen.cache import DocumentCache
from mock_gmail_api.docgen.content import StubBackend
from mock_gmail_api.faults import FaultProfile
from mock_gmail_api.generator.seed import GenerateConfig, generate
from mock_gmail_api.server import build_app

DEV_TOKEN = "test-token"


@pytest.fixture
def docgen_cache_dir(tmp_path: Path) -> Path:
    return tmp_path / "docgen_cache"


@pytest.fixture
def fixture_db(tmp_path: Path, docgen_cache_dir: Path) -> Path:
    # StubBackend, not the live `claude -p` backend: the test suite must run
    # fast and offline. See docgen/content.py's module docstring.
    docgen_cache = DocumentCache(cache_dir=docgen_cache_dir, backend=StubBackend())
    db_path = tmp_path / "fixtures.sqlite"
    generate(
        GenerateConfig(seed=42, volume=60, pitch_ratio=0.4, docgen_cache=docgen_cache), db_path
    )
    return db_path


@pytest.fixture
def client(fixture_db: Path, docgen_cache_dir: Path) -> Iterator[TestClient]:
    app = build_app(
        fixture_db,
        fault_profile=FaultProfile.none(),
        dev_token=DEV_TOKEN,
        docgen_cache_dir=docgen_cache_dir,
        # Never the live `claude -p` backend in tests — see docgen/content.py's
        # module docstring.
        docgen_backend="stub",
    )
    with TestClient(app) as test_client:
        test_client.headers["Authorization"] = f"Bearer {DEV_TOKEN}"
        yield test_client
