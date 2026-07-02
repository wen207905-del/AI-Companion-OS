"""Tests for stat_snapshot helpers."""

from chat.stat_snapshot import build_stat_update, compute_numeric_deltas


def test_compute_numeric_deltas_filters_small_changes():
    before = {"love": 70.0, "trust": 35.0}
    after = {"love": 72.5, "trust": 35.02}
    deltas = compute_numeric_deltas(before, after, ["love", "trust"])
    assert deltas == {"love": 2.5}


def test_build_stat_update_includes_relationship_and_xp():
    rel_before = {
        "stage_name": "朋友",
        "love": 50.0,
        "trust": 30.0,
        "attachment": 10.0,
        "respect": 20.0,
        "security": 10.0,
        "possessiveness": 5.0,
        "jealousy": 5.0,
        "intimacy_emotional": 5.0,
        "intimacy_physical": 5.0,
    }
    rel_after = dict(rel_before)
    rel_after["love"] = 55.0
    rel_after["stage_name"] = "暧昧"

    emo_before = {"primary_mood": "平静"}
    emo_after = {"primary_mood": "开心"}

    payload = build_stat_update(
        "test_char",
        rel_before,
        rel_after,
        emo_before,
        emo_after,
        {"xp": 10},
        {"xp": 18, "level": 1},
    )

    assert payload["type"] == "stat_update"
    assert payload["character_id"] == "test_char"
    assert payload["deltas"]["relationship"]["love"] == 5.0
    assert payload["deltas"]["xp"] == 8
    assert payload["deltas"]["stage_name"] == "暧昧"
    assert payload["deltas"]["mood"] == "开心"
