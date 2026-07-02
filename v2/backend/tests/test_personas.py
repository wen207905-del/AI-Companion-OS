"""Validate all persona YAML files."""

from pathlib import Path

import pytest
import yaml

from config import PERSONA_DIR

REQUIRED_ROOT_KEYS = ("id", "name", "type", "personality", "shared_history", "intimate_state", "chat_behavior")


@pytest.fixture
def all_personas():
    personas = {}
    for path in PERSONA_DIR.glob("*.yaml"):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        personas[data["id"]] = data
    return personas


def test_persona_count(all_personas):
    assert len(all_personas) >= 12


def test_persona_required_fields(all_personas):
    for pid, persona in all_personas.items():
        for key in REQUIRED_ROOT_KEYS:
            assert key in persona, f"{pid} missing {key}"


def test_persona_ids_match_filename(all_personas):
    for path in PERSONA_DIR.glob("*.yaml"):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["id"] == path.stem, f"file {path.name} id mismatch"


def test_female_personas_have_body_experiences(all_personas):
    for pid, persona in all_personas.items():
        if persona.get("relationship_type") == "brotherhood":
            continue
        if persona.get("gender") == "male":
            continue
        intimate = persona.get("intimate_state", {})
        assert intimate.get("body_experiences"), f"{pid} missing body_experiences"


def test_intimate_state_scores(all_personas):
    for pid, persona in all_personas.items():
        intimate = persona.get("intimate_state", {})
        if persona.get("relationship_type") == "brotherhood":
            continue
        affection = intimate.get("affection")
        assert affection is not None, f"{pid} missing affection"
        assert 0 <= affection <= 100, f"{pid} affection out of range"
