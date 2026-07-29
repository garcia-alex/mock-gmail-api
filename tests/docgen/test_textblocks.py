from __future__ import annotations

from mock_gmail_api.docgen.textblocks import parse_sections


def test_parses_headings_bullets_and_paragraphs() -> None:
    text = "## Problem\n- pain point one\n- pain point two\n\nSome narrative prose.\n"
    sections = parse_sections(text)

    assert len(sections) == 1
    assert sections[0].heading == "Problem"
    assert sections[0].blocks[0].kind == "bullets"
    assert sections[0].blocks[0].items == ["pain point one", "pain point two"]
    assert sections[0].blocks[1].kind == "paragraph"
    assert sections[0].blocks[1].text == "Some narrative prose."


def test_multiple_sections() -> None:
    text = "## First\n- a\n## Second\n- b\n- c\n"
    sections = parse_sections(text)

    assert [s.heading for s in sections] == ["First", "Second"]
    assert sections[1].blocks[0].items == ["b", "c"]


def test_no_heading_produces_untitled_section() -> None:
    sections = parse_sections("just a paragraph, no heading\n")
    assert len(sections) == 1
    assert sections[0].heading == ""


def test_empty_text_produces_no_sections() -> None:
    assert parse_sections("") == []
    assert parse_sections("   \n\n  ") == []
