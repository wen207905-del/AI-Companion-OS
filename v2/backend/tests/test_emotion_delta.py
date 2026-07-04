"""Tests for V4.1 emotion_delta on user interaction."""

from engine.emotion_engine import EmotionEngine
from engine.relationship_engine import RelationshipEngine


def test_user_reply_delta(memory_db):
    engine = EmotionEngine(memory_db)
    engine.init_character("test")
    applied = engine.apply_user_reply_delta(
        "test",
        "今天过得怎么样？还想和你多聊一会。",
        affection_grade="倾心",
    )
    summary = engine.get_summary("test")
    assert applied.get("happy", 0) > 0
    assert applied.get("miss_user", 0) < 0
    assert applied.get("lonely", 0) < 0
    assert summary["happy"] > 50


def test_perfunctory_reply_smaller_boost(memory_db):
    engine = EmotionEngine(memory_db)
    engine.init_character("test")
    rich = engine.apply_user_reply_delta("test", "今天过得怎么样？还想和你多聊一会。", affection_grade="倾心")
    engine.init_character("test2")
    short = engine.apply_user_reply_delta("test2", "在吗", affection_grade="倾心")
    assert rich.get("happy", 0) > short.get("happy", 0)


def test_apply_delta_clamps(memory_db):
    engine = EmotionEngine(memory_db)
    engine.init_character("test")
    engine.states["test"].happy = 98.0
    applied = engine.apply_delta("test", {"happy": 10.0})
    assert engine.states["test"].happy == 100.0
    assert applied["happy"] == 2.0


def test_user_message_emotion_updates_security(memory_db):
    rel_engine = RelationshipEngine(memory_db)
    rel_engine.init_character("test", {"intimate_state": {"affection": 70, "desire": {}}})
    emo_engine = EmotionEngine(memory_db)
    emo_engine.init_character("test")

    from app_state import state
    state.db = memory_db
    state.emo_engine = emo_engine
    state.rel_engine = rel_engine

    from services.emotion_tick import apply_user_message_emotion

    before = rel_engine.states["test"].security
    apply_user_message_emotion(
        "test",
        "刚下班，路上想到你了。",
        {"affection_grade": "倾心"},
    )
    assert rel_engine.states["test"].security > before
