"""Parser for the Gmail `q=` search grammar subset this mock supports:
`to:`, `from:`, `subject:`, `newer_than:<N><h|d|m>`, `older_than:<N><h|d|m>`,
`label:<LABEL>` (case-sensitive), `is:unread` (sugar for `label:UNREAD`),
`has:attachment`. Anything else is treated as a free-text term and, matching
real Gmail's lenient parser, unknown/malformed operator tokens are silently
folded into free-text rather than raising — logged, not errored.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_DURATION_RE = re.compile(r"(\d+)([hdm])")
_UNIT_TO_DAYS = {"h": 1 / 24, "d": 1, "m": 30}

_KNOWN_KEYS = frozenset({"to", "from", "subject", "newer_than", "older_than", "label", "is", "has"})


@dataclass(frozen=True, slots=True)
class ParsedQuery:
    free_terms: list[str] = field(default_factory=list)
    to: str | None = None
    from_: str | None = None
    subject: str | None = None
    newer_than_days: float | None = None
    older_than_days: float | None = None
    labels: frozenset[str] = field(default_factory=frozenset)
    has_attachment: bool = False


def _parse_duration(value: str) -> float | None:
    match = _DURATION_RE.fullmatch(value)
    if not match:
        return None
    amount, unit = match.groups()
    return _UNIT_TO_DAYS[unit] * int(amount)


def parse_query(query: str | None) -> ParsedQuery:
    if not query:
        return ParsedQuery()

    free_terms: list[str] = []
    to: str | None = None
    from_: str | None = None
    subject: str | None = None
    newer_than_days: float | None = None
    older_than_days: float | None = None
    labels: set[str] = set()
    has_attachment = False

    for token in query.split():
        key, sep, value = token.partition(":")
        key_lower = key.lower()
        if not sep or key_lower not in _KNOWN_KEYS or not value:
            free_terms.append(token)
            continue

        if key_lower == "to":
            to = value
        elif key_lower == "from":
            from_ = value
        elif key_lower == "subject":
            subject = value
        elif key_lower == "newer_than":
            days = _parse_duration(value)
            if days is None:
                logger.info("ignoring malformed newer_than token: %r", token)
                free_terms.append(token)
            else:
                newer_than_days = days
        elif key_lower == "older_than":
            days = _parse_duration(value)
            if days is None:
                logger.info("ignoring malformed older_than token: %r", token)
                free_terms.append(token)
            else:
                older_than_days = days
        elif key_lower == "label":
            labels.add(value)
        elif key_lower == "is":
            if value.lower() == "unread":
                labels.add("UNREAD")
            else:
                logger.info("ignoring unsupported is: token: %r", token)
                free_terms.append(token)
        elif key_lower == "has":
            if value.lower() == "attachment":
                has_attachment = True
            else:
                logger.info("ignoring unsupported has: token: %r", token)
                free_terms.append(token)

    return ParsedQuery(
        free_terms=free_terms,
        to=to,
        from_=from_,
        subject=subject,
        newer_than_days=newer_than_days,
        older_than_days=older_than_days,
        labels=frozenset(labels),
        has_attachment=has_attachment,
    )
