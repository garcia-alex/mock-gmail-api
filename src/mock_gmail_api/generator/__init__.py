from __future__ import annotations

from faker import Faker

_ID_PREFIXES = frozenset({"thr", "msg", "att", "drf"})


def new_id(fake: Faker, prefix: str) -> str:
    if prefix not in _ID_PREFIXES:
        raise ValueError(f"unknown id prefix: {prefix!r}")
    return f"{prefix}_{fake.random.getrandbits(64):016x}"


def slugify_company_name(company_name: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in company_name).strip("_")
