"""Tests for arousal engine."""

from engine.arousal_engine import ArousalEngine, arousal_tier_label


def test_arousal_rises_on_intimate_message(memory_db):
    engine = ArousalEngine(memory_db)
    engine.init_character("a", {"intimate_state": {"lewdness": 60, "desire": {"physical": 50}}})
    before = engine.states["a"].level
    delta = engine.process_message(
        "a",
        "过来亲我一下，想摸你的胸",
        {"love": 70, "intimacy_physical": 40, "attachment": 50},
        {"excited": 20, "shy": 15, "angry": 0, "sad": 0, "fearful": 0},
    )
    assert delta > 0
    assert engine.states["a"].level > before


def test_arousal_drops_on_rejection(memory_db):
    engine = ArousalEngine(memory_db)
    engine.init_character("a", {"intimate_state": {"lewdness": 50}})
    engine.states["a"].level = 55
    engine.process_message(
        "a",
        "不要碰我，滚",
        {"love": 70, "intimacy_physical": 30, "attachment": 40},
        {"angry": 30, "sad": 10, "fearful": 5, "excited": 0, "shy": 0},
    )
    assert engine.states["a"].level < 55


def test_tier_labels():
    assert arousal_tier_label(10) == "平静"
    assert arousal_tier_label(40) == "心动"
    assert arousal_tier_label(80) == "情动"
