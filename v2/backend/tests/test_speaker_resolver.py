"""Tests for scene participant detection."""

from config import PERSONA_DIR
from personality.persona_loader import PersonaLoader
from services.speaker_resolver import detect_participants


def test_detect_mama_alias_for_ye_ruxue():
    loader = PersonaLoader(PERSONA_DIR)
    found = detect_participants("傍晚我回家，妈妈在茶亭整理资料", loader)
    assert "ye_ruxue" in found


def test_detect_location_hint_kitchen():
    loader = PersonaLoader(PERSONA_DIR)
    found = detect_participants("我走进厨房，闻到排骨汤的味道", loader)
    assert "bai_rou" in found


def test_active_character_always_included():
    loader = PersonaLoader(PERSONA_DIR)
    found = detect_participants("今天天气不错", loader, active_character_id="ye_ruxue")
    assert found == ["ye_ruxue"]


def test_detect_multiple_by_name():
    loader = PersonaLoader(PERSONA_DIR)
    found = detect_participants("夜如雪和白柔都在客厅", loader)
    assert "ye_ruxue" in found
    assert "bai_rou" in found
