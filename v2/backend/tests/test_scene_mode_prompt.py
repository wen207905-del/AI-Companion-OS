"""Tests for scene mode prompt assembly."""

from app_state import state
from services.scene_mode_service import _load_template, _relation_network, build_scene_messages


def test_scene_template_structure():
    template = _load_template()
    assert "叙述模式" in template
    assert "{participant_roster}" in template
    assert "{user_name}" in template
    assert "narration" in template


def test_relation_network_empty():
    text = _relation_network([])
    assert "推断" in text or "persona" in text.lower()


def test_build_scene_messages_with_app(client):
    assert state.persona_loader is not None
    messages = build_scene_messages(
        "我推开门，看见妈妈在茶亭，白柔在厨房。",
        participant_ids=["ye_ruxue", "bai_rou"],
        active_character_id="ye_ruxue",
    )
    system = messages[0]["content"]
    assert "夜如雪" in system
    assert "白柔" in system
    assert "▸ ye_ruxue" in system
