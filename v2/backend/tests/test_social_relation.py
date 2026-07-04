"""Tests for V4.1 social relation service."""

from engine.relationship_engine import RelationshipEngine
from services.social_relation_service import (
    apply_init_to_engine,
    load_relationship_init,
    seed_all_characters,
    upsert_user_relation,
)


def test_load_relationship_init_has_twelve():
    init_map = load_relationship_init()
    assert len(init_map) == 12
    assert init_map["wang_dahai"]["relationship_type"] == "brotherhood"
    assert init_map["ye_ruxue"]["affection_score"] == 58


def test_seed_not_all_eighty(memory_db):
    engine = RelationshipEngine(memory_db)
    ids = list(load_relationship_init().keys())
    for cid in ids:
        engine.init_character(cid, {"relationship_type": "romance", "intimate_state": {"affection": 0}})

    count = seed_all_characters(engine, memory_db, ids, force=True)
    assert count == 12

    loves = [engine.states[cid].love for cid in ids]
    assert min(loves) < 80
    assert max(loves) > 80
    assert len(set(round(x) for x in loves)) >= 5


def test_wang_dahai_friendship(memory_db):
    engine = RelationshipEngine(memory_db)
    init = load_relationship_init()["wang_dahai"]
    apply_init_to_engine(engine, "wang_dahai", init)
    upsert_user_relation(memory_db, "wang_dahai", init)

    assert engine.relationship_types["wang_dahai"] == "brotherhood"
    assert engine.states["wang_dahai"].love == 82

    row = memory_db.execute(
        "SELECT affection_grade, social_relation_label FROM character_user_relation WHERE character_id = ?",
        ("wang_dahai",),
    ).fetchone()
    assert row["affection_grade"] == "铁哥们"
    assert row["social_relation_label"] == "兄弟"


def test_ye_ruxue_mentor_not_lover_stage(memory_db):
    engine = RelationshipEngine(memory_db)
    init = load_relationship_init()["ye_ruxue"]
    apply_init_to_engine(engine, "ye_ruxue", init)
    upsert_user_relation(memory_db, "ye_ruxue", init)

    assert engine.states["ye_ruxue"].love == 58
    row = memory_db.execute(
        "SELECT social_relation_label, affection_grade FROM character_user_relation WHERE character_id = ?",
        ("ye_ruxue",),
    ).fetchone()
    assert row["social_relation_label"] == "成熟引导者"
    assert row["affection_grade"] == "在意"
