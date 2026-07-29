"""Catalog of the synthetic document types this generator produces (pitch
decks, one-pagers, cap tables) — see the module docstring in
`mock_gmail_api.docgen` for why this exists.

The default prompts below are pitch-deck-specific, but callers aren't stuck
with that one scenario: `prompt_for` accepts an optional `custom_templates`
mapping (doc_type key -> a `str.format`-style template string using
`{company_name}`/`{sector}`/`{stage}`/`{ask}` placeholders) to swap in
their own domain-specific prompt content. `load_custom_templates` reads
such a mapping from a `.json` or `.yaml` file. When no custom templates are
supplied (or a given doc_type key isn't in them), `prompt_for` falls back
to the built-in `PitchMeta`-driven defaults.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from mock_gmail_api.models import PitchMeta

PDF = "application/pdf"
DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@dataclass(frozen=True, slots=True)
class DocType:
    key: str
    mimetype: str
    extension: str


def _pitch_deck_prompt(meta: PitchMeta) -> str:
    return (
        f"Write the text content of a venture-capital pitch deck for "
        f"{meta.company_name}, a {meta.sector} company raising a "
        f"{meta.stage} round of {meta.ask}. Structure it as slide-by-slide "
        f"content: a short title, then one slide per section covering "
        f"problem, solution, product, market size, traction, business "
        f"model, team, and the ask. For each slide, output a heading line "
        f"starting with '## ' followed by 2-4 concise bullet points "
        f"starting with '- '. Keep it plausible and specific to the "
        f"sector, not generic filler. Output only the slide content, no "
        f"preamble or explanation."
    )


def _one_pager_prompt(meta: PitchMeta) -> str:
    return (
        f"Write a one-page company memo for {meta.company_name}, a "
        f"{meta.sector} company raising a {meta.stage} round of "
        f"{meta.ask}. Structure it with a '## ' heading per section "
        f"covering: Overview, Problem, Product, Traction, Team, and The "
        f"Ask. Each section should be 2-4 sentences of plausible prose "
        f"specific to the sector. Output only the memo content, no "
        f"preamble or explanation."
    )


def _cap_table_prompt(meta: PitchMeta) -> str:
    return (
        f"Generate a plausible capitalization table for "
        f"{meta.company_name}, a {meta.sector} company that has raised "
        f"through {meta.stage}. Output ONLY a JSON array of objects, no "
        f"prose, no markdown fences. Each object must have exactly these "
        f"keys: 'holder' (string, e.g. a founder name or fund name), "
        f"'share_class' (string, e.g. 'Common' or 'Series Seed "
        f"Preferred'), 'shares' (integer), and 'ownership_pct' (number, "
        f"the percentage ownership rounded to 1 decimal place). Include "
        f"5-8 rows covering founders, an option pool, and one or more "
        f"investors, with ownership_pct values that sum to approximately "
        f"100."
    )


PITCH_DECK = DocType(key="pitch_deck", mimetype=PDF, extension="pdf")
ONE_PAGER = DocType(key="one_pager", mimetype=DOCX, extension="docx")
CAP_TABLE = DocType(key="cap_table", mimetype=XLSX, extension="xlsx")

_PROMPT_BUILDERS = {
    "pitch_deck": _pitch_deck_prompt,
    "one_pager": _one_pager_prompt,
    "cap_table": _cap_table_prompt,
}


def load_custom_templates(path: str | Path) -> dict[str, str]:
    """Load a caller-supplied mapping of doc_type key -> prompt template
    string from a `.json` or `.yaml`/`.yml` file, for use with `prompt_for`.
    """
    file_path = Path(path)
    if file_path.suffix in (".yaml", ".yml"):
        import yaml

        data = yaml.safe_load(file_path.read_text())
    elif file_path.suffix == ".json":
        data = json.loads(file_path.read_text())
    else:
        raise ValueError(
            f"unsupported custom template format: {file_path.suffix!r} "
            "(expected .json, .yaml, or .yml)"
        )
    if not isinstance(data, dict) or not all(isinstance(v, str) for v in data.values()):
        raise ValueError(
            f"{file_path}: custom template file must contain a mapping of "
            "doc_type key -> template string"
        )
    return data


def prompt_for(
    doc_type: DocType, meta: PitchMeta, custom_templates: dict[str, str] | None = None
) -> str:
    if custom_templates is not None and doc_type.key in custom_templates:
        return custom_templates[doc_type.key].format(
            company_name=meta.company_name, sector=meta.sector, stage=meta.stage, ask=meta.ask
        )
    return _PROMPT_BUILDERS[doc_type.key](meta)
