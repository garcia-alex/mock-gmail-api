from __future__ import annotations

from datetime import UTC, datetime

from mock_gmail_api.__main__ import _cmd_generate, build_parser


def test_reference_time_flag_parses_iso8601() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["generate", "--reference-time", "2030-01-01T00:00:00Z", "--db", "ignored.sqlite"]
    )
    assert args.reference_time == "2030-01-01T00:00:00Z"


def test_reference_time_defaults_to_none() -> None:
    parser = build_parser()
    args = parser.parse_args(["generate", "--db", "ignored.sqlite"])
    assert args.reference_time is None


def test_cmd_generate_wires_reference_time_into_config(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_generate(config, db_path) -> None:
        captured["reference_time"] = config.reference_time

    monkeypatch.setattr("mock_gmail_api.__main__.generate", fake_generate)

    parser = build_parser()
    db_path = tmp_path / "fixtures.sqlite"
    args = parser.parse_args(
        [
            "generate",
            "--reference-time",
            "2030-06-15T08:30:00Z",
            "--db",
            str(db_path),
            "--volume",
            "1",
        ]
    )
    _cmd_generate(args)

    assert captured["reference_time"] == datetime(2030, 6, 15, 8, 30, tzinfo=UTC)


def test_cmd_generate_omits_reference_time_uses_config_default(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_generate(config, db_path) -> None:
        captured["reference_time"] = config.reference_time

    monkeypatch.setattr("mock_gmail_api.__main__.generate", fake_generate)

    parser = build_parser()
    db_path = tmp_path / "fixtures.sqlite"
    args = parser.parse_args(["generate", "--db", str(db_path), "--volume", "1"])
    _cmd_generate(args)

    from mock_gmail_api.generator.seed import GenerateConfig

    assert captured["reference_time"] == GenerateConfig(seed=42).reference_time
