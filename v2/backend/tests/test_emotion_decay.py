"""Tests for V4.1 emotion decay tick."""

from engine.emotion_engine import EmotionEngine


def test_decay_tick_reduces_happy_and_raises_lonely(memory_db):
    engine = EmotionEngine(memory_db)
    engine.init_character("test")
    s = engine.states["test"]
    s.happy = 70.0
    s.lonely = 15.0
    s.miss_user = 20.0
    s.excited = 20.0

    for i in range(6):
        hours = (i + 1) * (5 / 60)
        engine.decay_tick("test", hours_since_user=hours, affection_grade="倾心")

    assert engine.states["test"].happy < 70.0
    assert engine.states["test"].excited < 20.0
    assert engine.states["test"].lonely > 15.0
    assert engine.states["test"].miss_user > 20.0


def test_decay_tick_calm_regresses_toward_center(memory_db):
    engine = EmotionEngine(memory_db)
    engine.init_character("test")
    engine.states["test"].calm = 70.0
    deltas = engine.decay_tick("test", hours_since_user=1.0, affection_grade="在意")
    assert engine.states["test"].calm < 70.0
    assert "calm" in deltas or engine.states["test"].calm < 70.0
