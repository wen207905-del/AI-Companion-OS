"""社会关系读写 — 世界观身份与好感等级分离存储。"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import yaml

from config import CONFIG_DIR
from engine.relationship_engine import RelationshipEngine, RelationshipState
from services.affection_grade_service import build_affection_display

INIT_PATH = CONFIG_DIR / "relationship_init.yaml"

_cached_init: dict[str, Any] | None = None


def load_relationship_init() -> dict[str, dict[str, Any]]:
    global _cached_init
    if _cached_init is not None:
        return _cached_init
    if not INIT_PATH.exists():
        _cached_init = {}
        return _cached_init
    with open(INIT_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _cached_init = data.get("characters") or {}
    return _cached_init


def _derive_dimensions(score: float, relationship_type: str) -> dict[str, float]:
    """从初始好感/友情分推导各关系维度（保持合理比例）。"""
    love = float(score)
    if relationship_type == "brotherhood":
        return {
            "love": love,
            "trust": min(100.0, love * 0.95),
            "attachment": min(100.0, love * 0.75),
            "respect": min(100.0, love * 0.85),
            "security": min(100.0, love * 0.80),
            "possessiveness": max(5.0, love * 0.15),
            "jealousy": max(3.0, love * 0.10),
            "intimacy_emotional": min(100.0, love * 0.55),
            "intimacy_physical": min(100.0, love * 0.25),
        }
    return {
        "love": love,
        "trust": min(100.0, love * 0.92),
        "attachment": min(100.0, love * 0.88),
        "respect": min(100.0, love * 0.82),
        "security": min(100.0, love * 0.85),
        "possessiveness": max(8.0, love * 0.35),
        "jealousy": max(5.0, love * 0.28),
        "intimacy_emotional": min(100.0, love * 0.90),
        "intimacy_physical": min(100.0, max(20.0, love * 0.55)),
    }


def apply_init_to_engine(
    rel_engine: RelationshipEngine,
    character_id: str,
    init_entry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """按 relationship_init.yaml 写入引擎内存状态。"""
    entry = init_entry or load_relationship_init().get(character_id)
    if not entry:
        return {}

    rel_type = entry.get("relationship_type", "romance")
    score = float(entry.get("affection_score", 50))
    dims = _derive_dimensions(score, rel_type)

    rel_engine.relationship_types[character_id] = rel_type
    state = rel_engine.states.get(character_id)
    if state is None:
        state = RelationshipState(character_id=character_id)
        rel_engine.states[character_id] = state

    for key, val in dims.items():
        setattr(state, key, val)
    state.clamp_all()
    return entry


def upsert_user_relation(db, character_id: str, entry: dict[str, Any]) -> None:
    rel_type = entry.get("relationship_type", "romance")
    score = float(entry.get("affection_score", 50))
    grade = entry.get("affection_grade") or build_affection_display(
        love=score,
        trust=score * 0.9,
        attachment=score * 0.85,
        security=score * 0.85,
        respect=score * 0.8,
        emotional_intimacy=score * 0.7,
        relationship_type=rel_type,
        preset_score=score,
    ).affection_grade

    db.execute(
        """
        INSERT INTO character_user_relation (
            character_id, social_relation_type, social_relation_label,
            affection_score, affection_grade, relationship_type,
            current_activity, current_addressing_style, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(character_id) DO UPDATE SET
            social_relation_type = excluded.social_relation_type,
            social_relation_label = excluded.social_relation_label,
            affection_score = excluded.affection_score,
            affection_grade = excluded.affection_grade,
            relationship_type = excluded.relationship_type,
            current_activity = excluded.current_activity,
            current_addressing_style = excluded.current_addressing_style,
            updated_at = excluded.updated_at
        """,
        (
            character_id,
            entry.get("social_relation_type", "friend"),
            entry.get("social_relation_label", "朋友"),
            score,
            grade,
            rel_type,
            entry.get("current_activity", "日常"),
            entry.get("current_addressing_style", ""),
            time.time(),
        ),
    )
    db.commit()


def seed_all_characters(
    rel_engine: RelationshipEngine,
    db,
    persona_ids: list[str],
    *,
    force: bool = False,
) -> int:
    """从 YAML 初始化角色。force=True 时覆盖已有记录（reset_world 用）。"""
    init_map = load_relationship_init()
    count = 0
    for cid in persona_ids:
        entry = init_map.get(cid)
        if not entry:
            continue
        if not force:
            row = db.execute(
                "SELECT 1 FROM character_user_relation WHERE character_id = ?",
                (cid,),
            ).fetchone()
            if row:
                continue
        apply_init_to_engine(rel_engine, cid, entry)
        upsert_user_relation(db, cid, entry)
        count += 1
    return count


def get_relation_meta(db, character_id: str) -> dict[str, Any]:
    row = db.execute(
        "SELECT * FROM character_user_relation WHERE character_id = ?",
        (character_id,),
    ).fetchone()
    if not row:
        return {}
    return {
        "social_relation_type": row["social_relation_type"],
        "social_relation_label": row["social_relation_label"],
        "affection_score": round(float(row["affection_score"]), 1),
        "affection_grade": row["affection_grade"],
        "current_activity": row["current_activity"] or "日常",
        "current_addressing_style": row["current_addressing_style"] or "",
    }


def enrich_relationship_summary(db, character_id: str, summary: dict[str, Any]) -> dict[str, Any]:
    """在 relationship get_summary 结果上附加社会关系与好感等级展示。"""
    if not summary:
        return summary
    meta = get_relation_meta(db, character_id)
    rel_type = summary.get("relationship_type", "romance")
    display = build_affection_display(
        love=float(summary.get("love", 0)),
        trust=float(summary.get("trust", 0)),
        attachment=float(summary.get("attachment", 0)),
        security=float(summary.get("security", 0)),
        respect=float(summary.get("respect", 0)),
        emotional_intimacy=float(summary.get("intimacy_emotional", 0)),
        relationship_type=rel_type,
        preset_score=meta.get("affection_score"),
        preset_grade=meta.get("affection_grade"),
    )
    out = {**summary, **meta}
    out["affection_score"] = display.affection_score
    out["affection_grade"] = display.affection_grade
    out["affection_label"] = display.score_label
    out["is_friendship"] = rel_type == "brotherhood"
    return out
