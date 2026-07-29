"""Tiny markdown-ish parser shared by the pdf/docx renderers: `## Heading`
lines start a new section, `- ` lines accumulate into a bullet list, any
other non-blank line is a paragraph. This is the shape the catalog's
pitch_deck/one_pager prompts ask the content backend to produce.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Block:
    kind: str  # "paragraph" | "bullets"
    text: str | None = None
    items: list[str] | None = None


@dataclass(frozen=True, slots=True)
class Section:
    heading: str
    blocks: list[Block]


def _flush_bullets(blocks: list[Block], bullets: list[str]) -> list[str]:
    if bullets:
        blocks.append(Block(kind="bullets", items=list(bullets)))
    return []


def parse_sections(text: str) -> list[Section]:
    sections: list[Section] = []
    heading = ""
    blocks: list[Block] = []
    bullets: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("## "):
            bullets = _flush_bullets(blocks, bullets)
            if heading or blocks:
                sections.append(Section(heading=heading, blocks=blocks))
            heading = line[3:].strip()
            blocks = []
        elif line.startswith("- "):
            bullets.append(line[2:].strip())
        else:
            bullets = _flush_bullets(blocks, bullets)
            blocks.append(Block(kind="paragraph", text=line))

    bullets = _flush_bullets(blocks, bullets)
    if heading or blocks:
        sections.append(Section(heading=heading, blocks=blocks))
    return sections
