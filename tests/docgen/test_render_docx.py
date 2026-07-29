from __future__ import annotations

import io

from docx import Document

from mock_gmail_api.docgen import render_docx


def test_render_produces_valid_docx_with_expected_text() -> None:
    text = "## Overview\nAcme Robotics builds robots.\n## The Ask\n- £1.5m Seed round\n"
    data = render_docx.render("Acme Robotics — One Pager", text)

    document = Document(io.BytesIO(data))
    all_text = "\n".join(p.text for p in document.paragraphs)

    assert "Acme Robotics — One Pager" in all_text
    assert "Overview" in all_text
    assert "Acme Robotics builds robots." in all_text
    assert "£1.5m Seed round" in all_text


def test_render_is_deterministic() -> None:
    text = "## Overview\nSame content every time.\n"
    first = render_docx.render("Title", text)
    second = render_docx.render("Title", text)

    assert first == second
