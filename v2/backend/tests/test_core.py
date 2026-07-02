"""Core engine and prompt tests."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.relationship_engine import RelationshipEngine
from engine.emotion_engine import EmotionEngine
from chat.prompt_builder import PromptBuilder
from config import init_db


def _memory_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def test_relationship_damping():
    db = _memory_db()
    engine = RelationshipEngine(db)
    persona = {"intimate_state": {"affection": 80, "desire": {}}}
    engine.init_character("test", persona)
    engine.apply_effect("test", "love", 10)
    assert engine.states["test"].love < 90


def test_relationship_load_from_db():
    db = _memory_db()
    engine = RelationshipEngine(db)
    persona = {"intimate_state": {"affection": 10, "desire": {}}}
    engine.init_character("test", persona)
    engine.apply_effect("test", "love", 5)
    engine.save_snapshot("test", "evt_1")

    engine2 = RelationshipEngine(db)
    engine2.init_character("test", persona)
    assert engine2.load_from_db("test")
    assert engine2.states["test"].love > 10


def test_prompt_builder_uses_core_personality():
    persona = {
        "name": "柳青柠",
        "type": "傲娇",
        "base_info": {"occupation": "大学生"},
        "personality": {"core": "教科书级别傲娇，嘴硬心软"},
        "speech_style": {"catchphrases": ["我才没有！", "哼，随便你。"]},
        "core_tags": ["傲娇", "嘴硬心软"],
    }
    builder = PromptBuilder(persona)
    system = builder.build_private_system(
        {"stage": 3, "stage_name": "朋友", "love": 40, "trust": 30},
        {"primary_mood": "平静"},
        {"private_tone": "别扭", "habits": ["哼"]},
    )
    assert "傲娇" in system
    assert "我才没有" in system or "嘴硬" in system


def test_emotion_decay():
    db = _memory_db()
    engine = EmotionEngine(db)
    engine.init_character("test")
    engine.states["test"].happy = 80
    engine.states["test"].last_update -= 7200
    engine.apply_decay("test")
    assert engine.states["test"].happy < 80


def test_prompt_builder_unrestricted_mode():
    import chat.prompt_builder as pb

    old = pb.CONTENT_MODE
    pb.CONTENT_MODE = "unrestricted"
    try:
        persona = {
            "name": "沈曼",
            "type": "大明星",
            "base_info": {"occupation": "演员"},
            "personality": {"private": {"summary": "私下软萌"}},
            "appearance": {"body": "H罩杯"},
            "intimate_state": {
                "fetishes": ["镜前亲密"],
                "sensitivity": {"neck": 9},
            },
            "taboos": {"red": ["禁止只夸身材"]},
            "speech_style": {"catchphrases": ["只给你看"]},
        }
        builder = PromptBuilder(persona)
        system = builder.build_private_system(
            {"stage": 6, "stage_name": "恋人", "love": 87, "trust": 86},
            {"primary_mood": "开心"},
            {"private_tone": "软", "habits": []},
        )
        assert "CG 互动小说" in system or "CG立绘" in system or "CG互动小说" in system
        assert "禁止只夸身材" in system
        assert "H罩杯" in system or "镜前亲密" in system
    finally:
        pb.CONTENT_MODE = old


if __name__ == "__main__":
    test_relationship_damping()
    test_relationship_load_from_db()
    test_prompt_builder_uses_core_personality()
    test_prompt_builder_unrestricted_mode()
    test_emotion_decay()
    print("All tests passed.")
