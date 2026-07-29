from __future__ import annotations

import json
from pathlib import Path

import pytest

from mock_gmail_api.docgen.catalog import CAP_TABLE, PITCH_DECK, load_custom_templates, prompt_for
from mock_gmail_api.models import PitchMeta

_META = PitchMeta(company_name="Acme Robotics", sector="Robotics", ask="£1.5m", stage="Seed")


def test_prompt_for_default_falls_back_to_builtin_builder() -> None:
    prompt = prompt_for(PITCH_DECK, _META)
    assert "Acme Robotics" in prompt
    assert "Robotics" in prompt


def test_prompt_for_uses_custom_template_when_key_present() -> None:
    custom_templates = {
        "pitch_deck": "Write a one-line summary for {company_name} ({sector}, {stage}, {ask}).",
    }
    prompt = prompt_for(PITCH_DECK, _META, custom_templates=custom_templates)
    assert prompt == "Write a one-line summary for Acme Robotics (Robotics, Seed, £1.5m)."


def test_prompt_for_falls_back_when_key_missing_from_custom_templates() -> None:
    custom_templates = {"pitch_deck": "custom {company_name}"}
    prompt = prompt_for(CAP_TABLE, _META, custom_templates=custom_templates)
    assert "custom" not in prompt
    assert "Acme Robotics" in prompt


def test_load_custom_templates_from_json(tmp_path: Path) -> None:
    path = tmp_path / "templates.json"
    path.write_text(json.dumps({"pitch_deck": "json template for {company_name}"}))

    templates = load_custom_templates(path)

    assert templates == {"pitch_deck": "json template for {company_name}"}


def test_load_custom_templates_from_yaml(tmp_path: Path) -> None:
    path = tmp_path / "templates.yaml"
    path.write_text("pitch_deck: yaml template for {company_name}\n")

    templates = load_custom_templates(path)

    assert templates == {"pitch_deck": "yaml template for {company_name}"}


def test_load_custom_templates_rejects_unknown_extension(tmp_path: Path) -> None:
    path = tmp_path / "templates.txt"
    path.write_text("pitch_deck: nope")

    with pytest.raises(ValueError, match="unsupported custom template format"):
        load_custom_templates(path)


def test_load_custom_templates_rejects_non_mapping(tmp_path: Path) -> None:
    path = tmp_path / "templates.json"
    path.write_text(json.dumps(["not", "a", "mapping"]))

    with pytest.raises(ValueError, match="mapping of doc_type key"):
        load_custom_templates(path)
