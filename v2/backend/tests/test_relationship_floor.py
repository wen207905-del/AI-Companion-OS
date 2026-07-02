"""Tests for relationship love floor."""

from engine.relationship_engine import RelationshipEngine


def test_ensure_minimum_love(memory_db):
    engine = RelationshipEngine(memory_db)
    engine.init_character("a", {"relationship_type": "romance", "intimate_state": {"affection": 10}})
    engine.init_character("b", {"relationship_type": "romance", "intimate_state": {"affection": 80}})
    engine.save_snapshot("a", "init")
    engine.save_snapshot("b", "init")

    updated = engine.ensure_minimum_love(70.0)

    assert updated == ["a"]
    assert engine.states["a"].love == 70.0
    assert engine.states["b"].love == 80.0
    assert engine.get_summary("a")["stage_name"] == "恋人"
