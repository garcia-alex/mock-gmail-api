from __future__ import annotations

from mock_gmail_api.docgen import render_pdf


def test_render_produces_valid_pdf_bytes() -> None:
    text = "## Problem\n- founders are tired\n- market is big\n\nSome plain prose too."
    data = render_pdf.render("Acme Robotics — Pitch Deck", text)

    assert data.startswith(b"%PDF-")
    assert data.rstrip().endswith(b"%%EOF")


def test_render_is_deterministic() -> None:
    text = "## Problem\n- founders are tired\n"
    first = render_pdf.render("Acme Robotics — Pitch Deck", text)
    second = render_pdf.render("Acme Robotics — Pitch Deck", text)

    assert first == second
