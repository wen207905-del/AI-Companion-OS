"""Tests for relationship love floor (legacy — V4.1 no longer forces uniform 80)."""

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


def test_reset_world_does_not_use_love_floor(memory_db):
    """V4.1: init from YAML keeps differentiated scores, not ensure_minimum_love(80)."""
    from services.social_relation_service import seed_all_characters

    engine = RelationshipEngine(memory_db)
    ids = ["ye_ruxue", "wang_dahai", "bai_rou"]
    for cid in ids:
        engine.init_character(cid, {"relationship_type": "romance", "intimate_state": {"affection": 0}})
    seed_all_characters(engine, memory_db, ids, force=True)

    assert engine.states["ye_ruxue"].love == 92
    assert engine.states["wang_dahai"].love == 82
    assert engine.states["bai_rou"].love == 86
