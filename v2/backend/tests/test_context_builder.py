"""Context builder tests."""

from chat.context_builder import boundary_hint_for, memory_block_for
from engine.boundary_engine import BoundaryEngine
from engine.emotion_engine import EmotionEngine
from engine.relationship_engine import RelationshipEngine
from memory.memory_manager import MemoryManager


def test_memory_block_for_character(memory_db):
    from app_state import state

    state.memory_manager = MemoryManager(memory_db)
    state.memory_manager.store("bai_rou", "做了红烧肉", role="character", scope="private")
    block = memory_block_for("bai_rou", "红烧肉", scope="private")
    assert "相关记忆" in block
    assert "红烧肉" in block


def test_boundary_hint_triggers(memory_db):
    from app_state import state

    state.rel_engine = RelationshipEngine(memory_db)
    state.emo_engine = EmotionEngine(memory_db)
    state.boundary_engine = BoundaryEngine()
    persona = {
        "intimate_state": {"affection": 80},
        "taboos": {"red": ["绝对无法接受出轨"], "yellow": []},
    }
    state.rel_engine.init_character("bai_rou", persona)
    state.emo_engine.init_character("bai_rou")

    hint = boundary_hint_for(persona, "你是不是出轨了", "bai_rou")
    assert "底线触发" in hint
