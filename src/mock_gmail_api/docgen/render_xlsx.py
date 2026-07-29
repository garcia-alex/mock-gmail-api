"""Render a JSON cap-table payload into an xlsx workbook using openpyxl."""

from __future__ import annotations

import io
import json
from datetime import UTC, datetime

from openpyxl import Workbook

_COLUMNS = ["holder", "share_class", "shares", "ownership_pct"]
_HEADERS = ["Holder", "Share Class", "Shares", "Ownership %"]

# Fixed rather than datetime.now(): openpyxl stamps workbook.properties with
# the wall-clock time at construction, which would otherwise make two
# renders of identical content byte-different (breaking the cache's
# same-input-same-output contract and generator_determinism tests).
_FIXED_TIMESTAMP = datetime(2026, 1, 1, tzinfo=UTC)


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```")
        stripped = stripped.removesuffix("```")
        stripped = stripped.strip()
    return stripped


def render(title: str, text: str) -> bytes:
    rows = json.loads(_strip_code_fence(text))

    workbook = Workbook()
    workbook.properties.created = _FIXED_TIMESTAMP
    workbook.properties.modified = _FIXED_TIMESTAMP
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "Cap Table"
    sheet.append([title])
    sheet.append(_HEADERS)
    for row in rows:
        sheet.append([row.get(column) for column in _COLUMNS])

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
