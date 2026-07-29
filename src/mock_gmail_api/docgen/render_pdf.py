"""Render parsed section content into a PDF using reportlab."""

from __future__ import annotations

import io

import reportlab.rl_config as rl_config
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from mock_gmail_api.docgen.textblocks import parse_sections

# Without this, reportlab embeds the wall-clock build time as the PDF's
# CreationDate, making two renders of identical content byte-different —
# breaks the cache's same-input-same-output contract and the generator
# determinism tests.
rl_config.invariant = 1


def render(title: str, text: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=LETTER, title=title)
    styles = getSampleStyleSheet()

    story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for section in parse_sections(text):
        if section.heading:
            story.append(Paragraph(section.heading, styles["Heading2"]))
        for block in section.blocks:
            if block.kind == "bullets" and block.items:
                for item in block.items:
                    story.append(Paragraph(f"&bull; {item}", styles["Normal"]))
            elif block.text:
                story.append(Paragraph(block.text, styles["Normal"]))
        story.append(Spacer(1, 10))

    doc.build(story)
    return buffer.getvalue()
