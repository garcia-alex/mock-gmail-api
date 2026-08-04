from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import uvicorn

from mock_gmail_api.docgen.cache import DocumentCache, default_cache_dir
from mock_gmail_api.docgen.content import get_backend
from mock_gmail_api.faults import Fault, FaultProfile
from mock_gmail_api.generator.seed import GenerateConfig, generate, generate_if_missing
from mock_gmail_api.server import build_app


def _parse_faults(raw: str) -> list[str]:
    if raw.strip().lower() in ("", "none"):
        return []
    names = [name.strip() for name in raw.split(",") if name.strip()]
    valid = {f.value for f in Fault}
    unknown = [n for n in names if n not in valid]
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown fault(s): {', '.join(unknown)} (valid: {', '.join(sorted(valid))})"
        )
    return names


def _cmd_generate(args: argparse.Namespace) -> int:
    docgen_cache = DocumentCache(
        cache_dir=Path(args.docgen_cache_dir), backend=get_backend(args.docgen_backend)
    )
    if args.reference_time is not None:
        config = GenerateConfig(
            seed=args.seed,
            volume=args.volume,
            pitch_ratio=args.pitch_ratio,
            reference_time=datetime.fromisoformat(args.reference_time.replace("Z", "+00:00")),
            docgen_cache=docgen_cache,
        )
    else:
        config = GenerateConfig(
            seed=args.seed,
            volume=args.volume,
            pitch_ratio=args.pitch_ratio,
            docgen_cache=docgen_cache,
        )
    if args.if_missing:
        ran = generate_if_missing(config, args.db)
        if not ran:
            print(f"{args.db} already exists — skipping generation (--if-missing)")
            return 0
    else:
        generate(config, args.db)
    print(f"Generated {args.db} (seed={args.seed}, volume={args.volume})")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    fault_names = _parse_faults(args.faults)
    fault_profile = (
        FaultProfile.from_names(fault_names, chance=args.fault_chance)
        if fault_names
        else FaultProfile.none()
    )
    app = build_app(
        args.db,
        fault_profile=fault_profile,
        dev_token=args.dev_token,
        docgen_cache_dir=args.docgen_cache_dir,
    )
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mock-gmail-api")
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen = subparsers.add_parser("generate", help="build/refresh the SQLite fixture database")
    gen.add_argument("--seed", type=int, default=int(os.environ.get("MOCK_GMAIL_SEED", "42")))
    gen.add_argument("--volume", type=int, default=200, help="approx. total messages generated")
    gen.add_argument("--pitch-ratio", type=float, default=0.3)
    gen.add_argument(
        "--reference-time",
        default=os.environ.get("MOCK_GMAIL_REFERENCE_TIME"),
        help="ISO8601 UTC timestamp messages are dated relative to (e.g. "
        "2026-08-04T12:00:00Z); omit to use the fixed default anchor "
        "(byte-identical fixtures across runs for the same seed)",
    )
    gen.add_argument("--db", default=os.environ.get("MOCK_GMAIL_DB", "./fixtures.sqlite"))
    gen.add_argument(
        "--if-missing",
        action="store_true",
        help="skip regeneration if the DB file already exists",
    )
    gen.add_argument(
        "--docgen-backend",
        default=os.environ.get("MOCK_GMAIL_DOCGEN_BACKEND", "live"),
        choices=["live", "stub"],
        help="'live' calls `claude -p` for realistic attachment content; "
        "'stub' fabricates content with Faker only (fast, no network)",
    )
    gen.add_argument(
        "--docgen-cache-dir",
        default=str(default_cache_dir()),
        help="directory generated attachment content is cached under, reused across runs",
    )
    gen.set_defaults(func=_cmd_generate)

    serve = subparsers.add_parser("serve", help="launch the HTTP server against a fixture DB")
    serve.add_argument("--db", default=os.environ.get("MOCK_GMAIL_DB", "./fixtures.sqlite"))
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument(
        "--dev-token",
        default=os.environ.get("MOCK_GMAIL_DEV_TOKEN"),
        help="if unset, any nonempty bearer token is accepted",
    )
    serve.add_argument(
        "--faults",
        default=os.environ.get("MOCK_GMAIL_FAULTS", "none"),
        help="comma-separated fault names (rate-limit,timeout,malformed,duplicate-page) or 'none'",
    )
    serve.add_argument(
        "--fault-chance",
        type=float,
        default=float(os.environ.get("MOCK_GMAIL_FAULT_CHANCE", "0.05")),
    )
    serve.add_argument(
        "--docgen-cache-dir",
        default=str(default_cache_dir()),
        help="directory generated attachment content is read from",
    )
    serve.set_defaults(func=_cmd_serve)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
