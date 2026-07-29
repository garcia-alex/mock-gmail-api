"""Configurable fault injection, applied inside route handlers so downstream
pipelines can exercise error-handling paths (rate limits, timeouts,
malformed payloads, duplicate pages) without special-cased test code.
Ported from mock-superhuman-mcp's `FaultProfile`, adapted for HTTP
semantics: rate-limit raises a real `HTTPException(429)` instead of a
transport-agnostic exception.
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from fastapi import HTTPException


class Fault(StrEnum):
    RATE_LIMIT = "rate-limit"
    TIMEOUT = "timeout"
    MALFORMED = "malformed"
    DUPLICATE_PAGE = "duplicate-page"


@dataclass(frozen=True, slots=True)
class FaultProfile:
    """Which faults are enabled and how often each fires, independently,
    per request. `chance` is the probability [0, 1] a given call trips that
    fault; a call can trip at most one fault.
    """

    enabled: frozenset[Fault] = field(default_factory=frozenset)
    chance: float = 0.05
    rng: random.Random = field(default_factory=random.Random)

    @classmethod
    def none(cls) -> FaultProfile:
        return cls(enabled=frozenset())

    @classmethod
    def from_names(
        cls, names: list[str], chance: float = 0.05, seed: int | None = None
    ) -> FaultProfile:
        enabled = frozenset(Fault(name) for name in names)
        rng = random.Random(seed) if seed is not None else random.Random()
        return cls(enabled=enabled, chance=chance, rng=rng)

    def roll(self) -> Fault | None:
        if not self.enabled:
            return None
        for fault in self.enabled:
            if self.rng.random() < self.chance:
                return fault
        return None


def apply_http(
    profile: FaultProfile,
    response: dict[str, Any],
    override_faults: list[str] | None = None,
    override_chance: float | None = None,
) -> dict[str, Any]:
    """Mutate/replace a would-be-successful response according to a rolled
    fault, or raise `HTTPException(429)` for rate-limit. `override_faults`/
    `override_chance` implement the per-request `X-Mock-Faults`/
    `X-Mock-Fault-Chance` header overrides.
    """
    active_profile = profile
    if override_faults is not None:
        active_profile = FaultProfile.from_names(
            override_faults,
            chance=override_chance if override_chance is not None else profile.chance,
            seed=None,
        )
    elif override_chance is not None:
        active_profile = FaultProfile(
            enabled=profile.enabled, chance=override_chance, rng=profile.rng
        )

    fault = active_profile.roll()
    if fault is None:
        return response

    if fault is Fault.RATE_LIMIT:
        raise HTTPException(status_code=429, detail="rate limit exceeded (synthetic fault)")

    if fault is Fault.TIMEOUT:
        time.sleep(active_profile.rng.uniform(1.0, 3.0))
        return response

    if fault is Fault.MALFORMED:
        malformed = dict(response)
        malformed.pop("id", None)
        malformed["__malformed__"] = True
        return malformed

    if fault is Fault.DUPLICATE_PAGE:
        items = response.get("messages")
        if isinstance(items, list) and items:
            response = dict(response)
            response["messages"] = [items[0], *items]
        return response

    return response
