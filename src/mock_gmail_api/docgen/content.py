"""Content backends: the piece that actually produces document text/data,
before it gets rendered into pdf/docx/xlsx bytes by the render_* modules.

Two backends:

- `LiveClaudeBackend` shells out to `claude -p` for genuinely realistic,
  sector-specific prose/data. This is what `mock-document-generation`
  means in practice, and what Ticket 0008's acceptance criteria refer to.
- `StubBackend` fabricates plausible-shaped content with Faker only, no
  subprocess/network call. It exists so the test suite (and any other
  caller that just needs *some* well-formed content fast) doesn't shell
  out to `claude -p` on every run — see docgen/__init__.py's module
  docstring for why that matters.

Both implement the same `generate(doc_type, meta) -> str` shape, so the
cache layer (docgen/cache.py) doesn't need to know which one it's driving.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from typing import Protocol

from faker import Faker

from mock_gmail_api.docgen.catalog import DocType, prompt_for
from mock_gmail_api.models import PitchMeta

BACKEND_ENV_VAR = "MOCK_GMAIL_DOCGEN_BACKEND"


class ContentBackend(Protocol):
    def generate(self, doc_type: DocType, meta: PitchMeta) -> str: ...


@dataclass(frozen=True, slots=True)
class LiveClaudeBackend:
    timeout_seconds: float = 120.0

    def generate(self, doc_type: DocType, meta: PitchMeta) -> str:
        prompt = prompt_for(doc_type, meta)
        try:
            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "the `claude` CLI is not on PATH — mock-document-generation's "
                "live backend requires it. Set "
                f"{BACKEND_ENV_VAR}=stub to use fabricated content instead."
            ) from exc
        if result.returncode != 0:
            raise RuntimeError(
                f"`claude -p` failed (exit {result.returncode}) generating "
                f"a {doc_type.key} for {meta.company_name}: {result.stderr.strip()}"
            )
        text = result.stdout.strip()
        if not text:
            raise RuntimeError(f"`claude -p` produced no output for {doc_type.key}")
        return text


def _seed_for(doc_type: DocType, meta: PitchMeta) -> int:
    payload = f"{doc_type.key}|{meta.company_name}|{meta.sector}|{meta.stage}|{meta.ask}"
    return int(hashlib.sha256(payload.encode()).hexdigest()[:8], 16)


def _stub_prose(fake: Faker, doc_type: DocType, meta: PitchMeta) -> str:
    sections = ["Overview", "Problem", "Product", "Traction", "Team", "The Ask"]
    if doc_type.key == "pitch_deck":
        sections = [
            "Problem",
            "Solution",
            "Product",
            "Market",
            "Traction",
            "Business Model",
            "Team",
            "The Ask",
        ]
    lines = [f"# {meta.company_name}"]
    for section in sections:
        lines.append(f"## {section}")
        for _ in range(fake.random_int(min=2, max=4)):
            lines.append(f"- {fake.sentence(nb_words=8)}")
    return "\n".join(lines)


def _stub_cap_table(fake: Faker, meta: PitchMeta) -> str:
    holders = [fake.name() for _ in range(fake.random_int(min=2, max=3))]
    rows = [
        {
            "holder": holder,
            "share_class": "Common",
            "shares": fake.random_int(min=500_000, max=2_000_000),
            "ownership_pct": round(fake.random.uniform(15.0, 35.0), 1),
        }
        for holder in holders
    ]
    rows.append(
        {
            "holder": "Option Pool",
            "share_class": "Common",
            "shares": fake.random_int(min=200_000, max=800_000),
            "ownership_pct": round(fake.random.uniform(8.0, 15.0), 1),
        }
    )
    rows.append(
        {
            "holder": f"{fake.last_name()} Capital",
            "share_class": f"{meta.stage} Preferred",
            "shares": fake.random_int(min=300_000, max=1_500_000),
            "ownership_pct": round(fake.random.uniform(10.0, 25.0), 1),
        }
    )
    return json.dumps(rows)


@dataclass(frozen=True, slots=True)
class StubBackend:
    def generate(self, doc_type: DocType, meta: PitchMeta) -> str:
        fake = Faker()
        fake.seed_instance(_seed_for(doc_type, meta))
        if doc_type.key == "cap_table":
            return _stub_cap_table(fake, meta)
        return _stub_prose(fake, doc_type, meta)


def get_backend(name: str | None = None) -> ContentBackend:
    resolved = name or os.environ.get(BACKEND_ENV_VAR, "live")
    if resolved == "live":
        return LiveClaudeBackend()
    if resolved == "stub":
        return StubBackend()
    raise ValueError(f"unknown docgen backend: {resolved!r} (expected 'live' or 'stub')")
