"""Build stat_update payloads for WebSocket after conversation events."""

from __future__ import annotations

REL_NUMERIC_KEYS = [
    "love",
    "trust",
    "attachment",
    "respect",
    "security",
    "possessiveness",
    "jealousy",
    "intimacy_emotional",
    "intimacy_physical",
]

EMO_NUMERIC_KEYS = [
    "happy", "calm", "stressed", "tired", "lonely",
    "excited", "embarrassed", "shy", "suspicious",
    "sad", "angry", "fearful",
]


def rel_numeric_snapshot(summary: dict) -> dict[str, float]:
    return {k: float(summary.get(k, 0)) for k in REL_NUMERIC_KEYS}


def compute_numeric_deltas(
    before: dict,
    after: dict,
    keys: list[str],
    threshold: float = 0.05,
) -> dict[str, float]:
    deltas: dict[str, float] = {}
    for key in keys:
        delta = round(float(after.get(key, 0)) - float(before.get(key, 0)), 1)
        if abs(delta) >= threshold:
            deltas[key] = delta
    return deltas


def build_stat_update(
    character_id: str,
    rel_before: dict,
    rel_after: dict,
    emo_before: dict,
    emo_after: dict,
    growth_before: dict | None = None,
    growth_after: dict | None = None,
    arousal_before: dict | None = None,
    arousal_after: dict | None = None,
) -> dict:
    rel_deltas = compute_numeric_deltas(
        rel_numeric_snapshot(rel_before),
        rel_numeric_snapshot(rel_after),
        REL_NUMERIC_KEYS,
    )
    emo_deltas = compute_numeric_deltas(
        {k: float(emo_before.get(k, 0)) for k in EMO_NUMERIC_KEYS},
        {k: float(emo_after.get(k, 0)) for k in EMO_NUMERIC_KEYS},
        EMO_NUMERIC_KEYS,
    )
    deltas: dict = {"relationship": rel_deltas}
    if emo_deltas:
        deltas["emotion"] = emo_deltas

    if growth_after is not None:
        xp_before = int((growth_before or {}).get("xp", 0))
        xp_after = int(growth_after.get("xp", 0))
        if xp_after > xp_before:
            deltas["xp"] = xp_after - xp_before

    stage_before = rel_before.get("stage_name")
    stage_after = rel_after.get("stage_name")
    if stage_before != stage_after and stage_after:
        deltas["stage_name"] = stage_after

    mood_before = emo_before.get("primary_mood")
    mood_after = emo_after.get("primary_mood")
    if mood_before != mood_after and mood_after:
        deltas["mood"] = mood_after

    if arousal_after is not None:
        level_before = float((arousal_before or {}).get("level", 0))
        level_after = float(arousal_after.get("level", 0))
        arousal_delta = round(level_after - level_before, 1)
        if abs(arousal_delta) >= 0.05:
            deltas["arousal"] = arousal_delta
        label_before = (arousal_before or {}).get("label")
        label_after = arousal_after.get("label")
        if label_before != label_after and label_after:
            deltas["arousal_label"] = label_after

    payload: dict = {
        "type": "stat_update",
        "character_id": character_id,
        "relationship": rel_after,
        "emotion": emo_after,
        "deltas": deltas,
    }
    if growth_after is not None:
        payload["growth"] = growth_after
    if arousal_after is not None:
        payload["arousal"] = arousal_after
    return payload
