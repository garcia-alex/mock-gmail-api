from __future__ import annotations

import pytest
from fastapi import HTTPException

from mock_gmail_api.faults import Fault, FaultProfile, apply_http


def test_no_fault_passes_through() -> None:
    profile = FaultProfile.none()
    response = {"id": "msg_1"}
    assert apply_http(profile, response) == response


def test_rate_limit_raises_429() -> None:
    profile = FaultProfile.from_names(["rate-limit"], chance=1.0, seed=1)
    with pytest.raises(HTTPException) as exc_info:
        apply_http(profile, {"id": "msg_1"})
    assert exc_info.value.status_code == 429


def test_timeout_sleeps_but_returns_response(monkeypatch: pytest.MonkeyPatch) -> None:
    slept: list[float] = []
    monkeypatch.setattr("mock_gmail_api.faults.time.sleep", lambda s: slept.append(s))
    profile = FaultProfile.from_names(["timeout"], chance=1.0, seed=1)
    response = apply_http(profile, {"id": "msg_1"})
    assert response == {"id": "msg_1"}
    assert len(slept) == 1


def test_malformed_strips_id_and_flags() -> None:
    profile = FaultProfile.from_names(["malformed"], chance=1.0, seed=1)
    response = apply_http(profile, {"id": "msg_1", "threadId": "thr_1"})
    assert "id" not in response
    assert response["__malformed__"] is True


def test_duplicate_page_duplicates_first_message() -> None:
    profile = FaultProfile.from_names(["duplicate-page"], chance=1.0, seed=1)
    response = apply_http(profile, {"messages": [{"id": "1"}, {"id": "2"}]})
    assert response["messages"] == [{"id": "1"}, {"id": "1"}, {"id": "2"}]


def test_header_override_faults() -> None:
    profile = FaultProfile.none()
    with pytest.raises(HTTPException):
        apply_http(profile, {"id": "msg_1"}, override_faults=["rate-limit"], override_chance=1.0)


def test_header_override_chance_zero_disables() -> None:
    profile = FaultProfile.from_names(["rate-limit"], chance=1.0, seed=1)
    response = apply_http(profile, {"id": "msg_1"}, override_chance=0.0)
    assert response == {"id": "msg_1"}


def test_fault_enum_values() -> None:
    assert {f.value for f in Fault} == {"rate-limit", "timeout", "malformed", "duplicate-page"}
