"""角色间关系读写 — 从 persona 初始化，供 DM 触发与 prompt 使用。"""

from __future__ import annotations

import time
from typing import Any

from config import USER_NAME

DEFAULT_RELATION = {
    "relation_label": "熟识",
    "familiarity": 50.0,
    "trust": 50.0,
    "affinity": 50.0,
    "rivalry": 0.0,
    "jealousy": 0.0,
    "respect": 50.0,
    "protectiveness": 30.0,
}


def _infer_rivalry(role: str, interaction: str) -> float:
    text = f"{role} {interaction}"
    if any(k in text for k in ("情敌", "吃醋", "rival", "竞争", "看不顺眼")):
        return 65.0
    if any(k in text for k in ("冤家", "互怼", "斗嘴")):
        return 45.0
    return 15.0


def _infer_label(role: str, interaction: str) -> str:
    text = f"{role} {interaction}"
    if "情敌" in text or "吃醋" in text:
        return "情敌"
    if "冤家" in text or "互怼" in text:
        return "竞争者"
    if "长辈" in text or "继母" in text or "阿姨" in text:
        return "长辈感"
    if "妻子" in text or "嫂子" in text:
        return "表面和平"
    if "朋友" in text or "闺蜜" in text:
        return "朋友"
    if "兄弟" in text or "发小" in text:
        return "朋友"
    return "熟识"


def upsert_relation(
    db,
    from_id: str,
    to_id: str,
    *,
    relation_label: str = "熟识",
    familiarity: float = 50.0,
    trust: float = 50.0,
    affinity: float = 50.0,
    rivalry: float = 0.0,
    jealousy: float = 0.0,
    respect: float = 50.0,
    protectiveness: float = 30.0,
) -> None:
    now = time.time()
    db.execute(
        """
        INSERT INTO character_character_relation (
            from_character_id, to_character_id, relation_label,
            familiarity, trust, affinity, rivalry, jealousy,
            respect, protectiveness, last_dm_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
        ON CONFLICT(from_character_id, to_character_id) DO UPDATE SET
            relation_label = excluded.relation_label,
            familiarity = excluded.familiarity,
            trust = excluded.trust,
            affinity = excluded.affinity,
            rivalry = excluded.rivalry,
            jealousy = excluded.jealousy,
            respect = excluded.respect,
            protectiveness = excluded.protectiveness,
            updated_at = excluded.updated_at
        """,
        (
            from_id, to_id, relation_label,
            familiarity, trust, affinity, rivalry, jealousy,
            respect, protectiveness, now,
        ),
    )


def seed_from_personas(db, persona_loader, *, force: bool = False) -> int:
    count = 0
    for pid, persona in persona_loader.personas.items():
        rels = persona.get("character_relations") or {}
        for target_id, meta in rels.items():
            if target_id not in persona_loader.personas:
                continue
            if not force:
                row = db.execute(
                    "SELECT 1 FROM character_character_relation WHERE from_character_id = ? AND to_character_id = ?",
                    (pid, target_id),
                ).fetchone()
                if row:
                    continue
            if not isinstance(meta, dict):
                continue
            role = str(meta.get("role") or "")
            interaction = str(meta.get("interaction") or "")
            rivalry = _infer_rivalry(role, interaction)
            label = _infer_label(role, interaction)
            upsert_relation(
                db, pid, target_id,
                relation_label=label,
                familiarity=55.0,
                trust=50.0,
                affinity=48.0,
                rivalry=rivalry,
                jealousy=min(70.0, rivalry * 0.6),
                respect=60.0 if "长辈" in role else 50.0,
                protectiveness=40.0,
            )
            count += 1
    db.commit()
    return count


def get_relation(db, from_id: str, to_id: str) -> dict[str, Any]:
    row = db.execute(
        "SELECT * FROM character_character_relation WHERE from_character_id = ? AND to_character_id = ?",
        (from_id, to_id),
    ).fetchone()
    if row:
        return dict(row)
    return {**DEFAULT_RELATION, "from_character_id": from_id, "to_character_id": to_id}


def relation_prompt_line(db, from_id: str, to_id: str, persona_loader) -> str:
    rel = get_relation(db, from_id, to_id)
    from_name = persona_loader.get_display_name(from_id)
    to_name = persona_loader.get_display_name(to_id)
    return (
        f"{from_name}→{to_name}：{rel.get('relation_label', '熟识')} "
        f"（熟悉{rel.get('familiarity', 50):.0f} 竞争{rel.get('rivalry', 0):.0f}）"
    )


def touch_dm(db, from_id: str, to_id: str) -> None:
    now = time.time()
    db.execute(
        """
        UPDATE character_character_relation
        SET last_dm_at = ?, updated_at = ?
        WHERE from_character_id = ? AND to_character_id = ?
        """,
        (now, now, from_id, to_id),
    )
    db.commit()
