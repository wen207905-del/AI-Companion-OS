"""实时发情度（情欲值）引擎 — 受对话、关系、情绪与人设影响。"""

from __future__ import annotations

import time
from dataclasses import dataclass


AROUSAL_TIERS: list[tuple[int, str]] = [
    (0, "平静"),
    (16, "微热"),
    (36, "心动"),
    (56, "升温"),
    (76, "情动"),
    (91, "失控"),
]

# 关键词 → 基础发情增量（再乘 susceptibility 与上下文系数）
AROUSAL_KEYWORDS: dict[str, float] = {
    "亲": 8, "吻": 10, "摸": 9, "抱": 6, "贴": 7, "蹭": 8,
    "胸": 12, "奶": 11, "臀": 10, "腿": 7, "腰": 7, "脖": 8,
    "脱": 14, "裸": 15, "硬": 13, "湿": 16, "潮": 14, "流": 12,
    "想要": 11, "要你": 12, "做": 9, "床": 10, "睡": 6,
    "舔": 14, "吮": 13, "咬": 9, "叫": 8, "喘": 12,
    "宝贝": 5, "姐姐": 5, "哥哥": 5, "老婆": 7, "老公": 7,
    "妈妈": 8, "爸爸": 7, "乖": 6, "骚": 13, "色": 10,
    "内衣": 11, "睡裙": 10, "丝袜": 11, "语音": 6, "照片": 8,
    "摸我": 14, "进来": 15, "深一点": 14, "轻点": 5,
}

AROUSAL_NEGATIVE: dict[str, float] = {
    "不要": -10, "停下": -12, "滚": -14, "恶心": -16, "变态": -10,
    "冷静": -8, "出去": -10, "别碰": -11,
}


def arousal_tier_label(level: float) -> str:
    label = AROUSAL_TIERS[0][1]
    for threshold, name in AROUSAL_TIERS:
        if level >= threshold:
            label = name
    return label


@dataclass
class ArousalState:
    character_id: str
    level: float = 0.0
    baseline: float = 12.0
    susceptibility: float = 1.0
    last_update: float = 0.0


class ArousalEngine:
    """管理角色当前发情度：对话升温、自然回落。"""

    def __init__(self, db) -> None:
        self.db = db
        self.states: dict[str, ArousalState] = {}
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS arousal_snapshot (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id TEXT NOT NULL,
                event_id TEXT,
                level REAL NOT NULL,
                baseline REAL NOT NULL,
                susceptibility REAL NOT NULL,
                timestamp REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_arousal_character
                ON arousal_snapshot(character_id, timestamp);
        """)
        self.db.commit()

    def init_character(self, character_id: str, persona: dict) -> None:
        intimate = persona.get("intimate_state") or {}
        lewdness = float(intimate.get("lewdness", 50))
        desire = intimate.get("desire") or {}
        physical = float(desire.get("physical", lewdness * 0.6))
        baseline = max(5.0, min(35.0, lewdness * 0.18 + physical * 0.08))
        susceptibility = max(0.45, min(1.65, 0.55 + lewdness / 100.0))
        self.states[character_id] = ArousalState(
            character_id=character_id,
            level=baseline,
            baseline=baseline,
            susceptibility=susceptibility,
            last_update=time.time(),
        )

    def load_from_db(self, character_id: str) -> bool:
        if character_id not in self.states:
            return False
        cur = self.db.execute(
            """
            SELECT level, baseline, susceptibility, timestamp
            FROM arousal_snapshot
            WHERE character_id = ? AND COALESCE(event_id, '') != 'init'
            ORDER BY timestamp DESC, id DESC
            LIMIT 1
            """,
            (character_id,),
        )
        row = cur.fetchone()
        if row is None:
            cur = self.db.execute(
                """
                SELECT level, baseline, susceptibility, timestamp
                FROM arousal_snapshot
                WHERE character_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT 1
                """,
                (character_id,),
            )
            row = cur.fetchone()
        if row is None:
            return False
        s = self.states[character_id]
        s.level = max(0.0, min(100.0, float(row["level"])))
        s.baseline = float(row["baseline"])
        s.susceptibility = float(row["susceptibility"])
        s.last_update = float(row["timestamp"])
        return True

    def apply_decay(self, character_id: str) -> None:
        if character_id not in self.states:
            return
        s = self.states[character_id]
        now = time.time()
        hours = max(0.0, (now - s.last_update) / 3600.0)
        if hours < 0.01:
            return
        if s.level > s.baseline:
            s.level = max(s.baseline, s.level - 12.0 * hours)
        elif s.level < s.baseline:
            s.level = min(s.baseline, s.level + 3.0 * hours)
        s.last_update = now

    def process_message(
        self,
        character_id: str,
        text: str,
        rel_summary: dict,
        emo_summary: dict,
        *,
        scale: float = 1.0,
    ) -> float:
        """根据用户消息与当前关系/情绪更新发情度，返回本句增量。"""
        if character_id not in self.states or not (text or "").strip():
            return 0.0
        s = self.states[character_id]
        self.apply_decay(character_id)

        msg = text.strip()
        delta = 0.0
        for kw, d in AROUSAL_KEYWORDS.items():
            if kw in msg:
                delta += d
        for kw, d in AROUSAL_NEGATIVE.items():
            if kw in msg:
                delta += d

        love = float(rel_summary.get("love", 0))
        intimacy = float(rel_summary.get("intimacy_physical", 0))
        attachment = float(rel_summary.get("attachment", 0))

        context_mul = 1.0
        context_mul += love / 100.0 * 0.35
        context_mul += intimacy / 100.0 * 0.45
        context_mul += attachment / 100.0 * 0.15

        excited = float(emo_summary.get("excited", 0))
        shy = float(emo_summary.get("shy", 0))
        embarrassed = float(emo_summary.get("embarrassed", 0))
        angry = float(emo_summary.get("angry", 0))
        sad = float(emo_summary.get("sad", 0))
        fearful = float(emo_summary.get("fearful", 0))

        if delta > 0:
            context_mul += excited / 100.0 * 0.25
            context_mul += (shy + embarrassed) / 100.0 * 0.2
        context_mul -= angry / 100.0 * 0.3
        context_mul -= (sad + fearful) / 100.0 * 0.15
        context_mul = max(0.35, min(2.2, context_mul))

        if delta == 0 and love >= 50:
            delta = 0.8 + intimacy / 100.0 * 0.6

        effective = delta * s.susceptibility * context_mul * scale
        if effective > 0 and s.level >= 85:
            effective *= 0.55
        s.level = max(0.0, min(100.0, s.level + effective))
        s.last_update = time.time()
        return round(effective, 2)

    def save_snapshot(self, character_id: str, event_id: str = "init") -> None:
        if character_id not in self.states:
            return
        s = self.states[character_id]
        self.db.execute(
            """
            INSERT INTO arousal_snapshot
            (character_id, event_id, level, baseline, susceptibility, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                character_id,
                event_id,
                s.level,
                s.baseline,
                s.susceptibility,
                time.time(),
            ),
        )
        self.db.commit()

    def get_summary(self, character_id: str) -> dict:
        if character_id not in self.states:
            return {}
        self.apply_decay(character_id)
        s = self.states[character_id]
        level = round(s.level, 1)
        return {
            "character_id": character_id,
            "level": level,
            "baseline": round(s.baseline, 1),
            "label": arousal_tier_label(level),
            "susceptibility": round(s.susceptibility, 2),
        }
