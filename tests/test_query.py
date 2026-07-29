from __future__ import annotations

from mock_gmail_api.query import parse_query


def test_stage0_query() -> None:
    parsed = parse_query("to:pitches@acme.example newer_than:1d")
    assert parsed.to == "pitches@acme.example"
    assert parsed.newer_than_days == 1
    assert parsed.free_terms == []


def test_from_and_subject() -> None:
    parsed = parse_query("from:founder@acme.com subject:deck")
    assert parsed.from_ == "founder@acme.com"
    assert parsed.subject == "deck"


def test_older_than() -> None:
    parsed = parse_query("older_than:7d")
    assert parsed.older_than_days == 7


def test_is_unread_sugar() -> None:
    parsed = parse_query("is:unread")
    assert "UNREAD" in parsed.labels


def test_has_attachment() -> None:
    parsed = parse_query("has:attachment")
    assert parsed.has_attachment is True


def test_label_case_sensitive() -> None:
    parsed = parse_query("label:PITCH-INBOUND")
    assert "PITCH-INBOUND" in parsed.labels


def test_free_text_terms() -> None:
    parsed = parse_query("urgent deck review")
    assert parsed.free_terms == ["urgent", "deck", "review"]


def test_unknown_operator_falls_back_to_free_text() -> None:
    parsed = parse_query("bogus:value")
    assert parsed.free_terms == ["bogus:value"]


def test_malformed_newer_than_falls_back_to_free_text() -> None:
    parsed = parse_query("newer_than:soon")
    assert parsed.newer_than_days is None
    assert parsed.free_terms == ["newer_than:soon"]


def test_empty_query() -> None:
    parsed = parse_query(None)
    assert parsed.free_terms == []
    assert parsed.to is None


def test_combined_query() -> None:
    parsed = parse_query("to:pitches@acme.example label:PITCH-INBOUND has:attachment is:unread")
    assert parsed.to == "pitches@acme.example"
    assert "PITCH-INBOUND" in parsed.labels
    assert "UNREAD" in parsed.labels
    assert parsed.has_attachment is True
