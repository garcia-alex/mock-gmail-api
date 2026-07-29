from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from mock_gmail_api.faults import FaultProfile
from mock_gmail_api.server import build_app


def test_missing_auth_header_401(fixture_db: Path) -> None:
    app = build_app(fixture_db, fault_profile=FaultProfile.none(), dev_token="secret")
    with TestClient(app) as c:
        resp = c.get("/gmail/v1/users/me/labels")
    assert resp.status_code == 401


def test_wrong_token_401_when_dev_token_set(fixture_db: Path) -> None:
    app = build_app(fixture_db, fault_profile=FaultProfile.none(), dev_token="secret")
    with TestClient(app) as c:
        resp = c.get("/gmail/v1/users/me/labels", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401


def test_correct_token_200_when_dev_token_set(fixture_db: Path) -> None:
    app = build_app(fixture_db, fault_profile=FaultProfile.none(), dev_token="secret")
    with TestClient(app) as c:
        resp = c.get("/gmail/v1/users/me/labels", headers={"Authorization": "Bearer secret"})
    assert resp.status_code == 200


def test_any_nonempty_token_accepted_when_dev_token_unset(fixture_db: Path) -> None:
    app = build_app(fixture_db, fault_profile=FaultProfile.none(), dev_token=None)
    with TestClient(app) as c:
        resp = c.get("/gmail/v1/users/me/labels", headers={"Authorization": "Bearer anything"})
    assert resp.status_code == 200


def test_health_endpoint_is_unauthenticated(fixture_db: Path) -> None:
    app = build_app(fixture_db, fault_profile=FaultProfile.none(), dev_token="secret")
    with TestClient(app) as c:
        resp = c.get("/health")
    assert resp.status_code == 200
