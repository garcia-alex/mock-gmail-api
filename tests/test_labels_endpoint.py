from __future__ import annotations

from fastapi.testclient import TestClient

from mock_gmail_api.db import SYSTEM_LABELS


def test_labels_include_system_labels(client: TestClient) -> None:
    resp = client.get("/gmail/v1/users/me/labels")
    assert resp.status_code == 200
    ids = {label["id"] for label in resp.json()["labels"]}
    assert set(SYSTEM_LABELS).issubset(ids)


def test_labels_include_pitch_label(client: TestClient) -> None:
    resp = client.get("/gmail/v1/users/me/labels")
    ids = {label["id"] for label in resp.json()["labels"]}
    assert "PITCH-INBOUND" in ids
