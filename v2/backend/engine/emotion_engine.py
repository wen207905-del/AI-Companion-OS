"""
情绪引擎 V2：实时情绪系统，支持自然衰减与 V4.1 emotion_delta。
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from engine.world_clock import TIMEZONE


@dataclass
class EmotionState:
    character_id: str
    happy: float = 50
    calm: float = 50
    stressed: float = 20
    tired: float = 20
    lonely: float = 15
    excited: float = 10
    embarrassed: float = 0
    shy: float = 20
    suspicious: float = 5
    sad: float = 5
    angry: float = 5
    fearful: float = 5
    miss_user: float = 20
    jealous: float = 0
    last_update: float = 0.0

    _dimensions = [
        "happy", "calm", "stressed", "tired", "lonely", "excited",
        "embarrassed", "shy", "suspicious", "sad", "angry", "fearful",
        "miss_user", "jealous",
    ]


MISS_USER_GRADE_COEF = {
    "灵魂牵系": 1.6, "羁绊": 1.55, "深恋": 1.5, "爱慕": 1.3, "倾心": 1.0,
    "在意": 0.8, "亲近": 0.7, "熟识": 0.5, "点头之交": 0.35, "陌生": 0.3,
    "过命兄弟": 0.6, "铁哥们": 0.5, "好兄弟": 0.45, "朋友": 0.4, "熟人": 0.35, "不熟": 0.3,
}

MISS_USER_REPLY_RELIEF = {
    "灵魂牵系": 15, "羁绊": 14, "深恋": 15, "爱慕": 12, "倾心": 10,
    "在意": 8, "亲近": 7, "熟识": 6, "点头之交": 5, "陌生": 5,
    "过命兄弟": 6, "铁哥们": 5, "好兄弟": 5, "朋友": 4, "熟人": 4, "不熟": 3,
}

LONELY_REPLY_RELIEF = {
    "深恋": 10, "爱慕": 9, "倾心": 8, "在意": 6, "铁哥们": 5, "default": 5,
}


class EmotionEngine:
    """情绪引擎：管理实时情绪 + 自然衰减"""

    DECAY_RATES = {
        "happy": 2, "excited": 5, "stressed": 3, "angry": 4,
        "sad": 3, "fearful": 3, "embarrassed": 4, "shy": 2,
        "suspicious": 2, "lonely": 1, "tired": 3,
    }

    TICK_DECAY = {
        "happy": 0.3,
        "excited": 0.5,
        "angry": 0.8,
        "shy": 0.2,
        "embarrassed": 0.3,
    }

    def __init__(self, db_conn):
        self.db = db_conn
        self.states: dict[str, EmotionState] = {}

    def init_character(self, character_id: str):
        self.states[character_id] = EmotionState(
            character_id=character_id,
            last_update=time.time(),
        )

    def _snapshot_columns(self) -> set[str]:
        try:
            rows = self.db.execute("PRAGMA table_info(emotion_snapshot)").fetchall()
            return {row["name"] for row in rows}
        except Exception:
            return set()

    def load_from_db(self, character_id: str) -> bool:
        if character_id not in self.states:
            return False
        cols = self._snapshot_columns()
        extra = ", miss_user, jealous" if "miss_user" in cols else ""
        cur = self.db.execute(f"""
            SELECT happy, calm, stressed, tired, lonely, excited,
                   embarrassed, shy, suspicious, sad, angry, fearful{extra}, timestamp
            FROM emotion_snapshot
            WHERE character_id = ? AND COALESCE(event_id, '') != 'init'
            ORDER BY timestamp DESC, id DESC
            LIMIT 1
        """, (character_id,))
        row = cur.fetchone()
        if row is None:
            cur = self.db.execute(f"""
                SELECT happy, calm, stressed, tired, lonely, excited,
                       embarrassed, shy, suspicious, sad, angry, fearful{extra}, timestamp
                FROM emotion_snapshot
                WHERE character_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT 1
            """, (character_id,))
            row = cur.fetchone()
        if row is None:
            return False

        s = self.states[character_id]
        s.happy = float(row["happy"])
        s.calm = float(row["calm"])
        s.stressed = float(row["stressed"])
        s.tired = float(row["tired"])
        s.lonely = float(row["lonely"])
        s.excited = float(row["excited"])
        s.embarrassed = float(row["embarrassed"])
        s.shy = float(row["shy"])
        s.suspicious = float(row["suspicious"])
        s.sad = float(row["sad"])
        s.angry = float(row["angry"])
        s.fearful = float(row["fearful"])
        if "miss_user" in row.keys():
            s.miss_user = float(row["miss_user"] or 20)
            s.jealous = float(row["jealous"] or 0)
        s.last_update = float(row["timestamp"])
        return True

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(100.0, value))

    def apply_delta(self, character_id: str, deltas: dict[str, float]) -> dict[str, float]:
        if character_id not in self.states or not deltas:
            return {}
        s = self.states[character_id]
        applied: dict[str, float] = {}
        for field, delta in deltas.items():
            if not hasattr(s, field):
                continue
            before = float(getattr(s, field))
            after = self._clamp(before + float(delta))
            setattr(s, field, after)
            change = round(after - before, 2)
            if abs(change) >= 0.05:
                applied[field] = change
        if applied:
            s.last_update = time.time()
        return applied

    def apply_decay(self, character_id: str):
        if character_id not in self.states:
            return
        s = self.states[character_id]
        now = time.time()
        hours = max(0, (now - s.last_update) / 3600)
        if hours < 0.01:
            return

        for field, rate in self.DECAY_RATES.items():
            current = getattr(s, field)
            if current > 0:
                decay = rate * hours
                setattr(s, field, max(0, current - decay))
        s.last_update = now

    def decay_tick(
        self,
        character_id: str,
        *,
        hours_since_user: float = 0.0,
        affection_grade: str = "在意",
    ) -> dict[str, float]:
        """V4.1 每 5 分钟 tick 衰减/漂移。"""
        if character_id not in self.states:
            return {}
        s = self.states[character_id]
        before = self._vector(s)
        deltas: dict[str, float] = {}

        for field, amount in self.TICK_DECAY.items():
            current = getattr(s, field)
            if current > 0:
                setattr(s, field, max(0.0, current - amount))

        hour = datetime.now(tz=ZoneInfo(TIMEZONE)).hour
        tired_bump = 0.2 + (0.5 if hour >= 22 or hour < 6 else 0.0)
        s.tired = self._clamp(s.tired + tired_bump)

        lonely_bump = min(3.0, 0.1 * max(0.0, hours_since_user))
        if lonely_bump > 0:
            s.lonely = self._clamp(s.lonely + lonely_bump)

        miss_coef = MISS_USER_GRADE_COEF.get(affection_grade, 0.8)
        miss_bump = 0.15 * miss_coef
        if hours_since_user >= 0.5:
            s.miss_user = self._clamp(s.miss_user + miss_bump)

        if s.calm > 50:
            s.calm = self._clamp(s.calm - 0.2)
        elif s.calm < 50:
            s.calm = self._clamp(s.calm + 0.2)

        s.last_update = time.time()
        after = self._vector(s)
        for key in before:
            change = round(after[key] - before[key], 2)
            if abs(change) >= 0.05:
                deltas[key] = change
        return deltas

    def apply_user_reply_delta(
        self,
        character_id: str,
        user_message: str,
        *,
        affection_grade: str = "在意",
    ) -> dict[str, float]:
        if character_id not in self.states:
            return {}
        text = (user_message or "").strip()
        if not text:
            return {}

        perfunctory = len(text) <= 4 or text in {"在吗", "嗯", "哦", "好", "ok", "OK"}
        happy_bump = 2.0 if perfunctory else min(6.0, 2.0 + len(text) * 0.08)
        miss_relief = float(MISS_USER_REPLY_RELIEF.get(affection_grade, 8))
        lonely_relief = float(LONELY_REPLY_RELIEF.get(affection_grade, LONELY_REPLY_RELIEF["default"]))
        security_bump = -1.0 if perfunctory else min(5.0, 1.0 + len(text) * 0.05)

        deltas = {
            "happy": happy_bump,
            "miss_user": -miss_relief,
            "lonely": -lonely_relief,
        }
        if not perfunctory:
            deltas["calm"] = 1.5
        return self.apply_delta(character_id, deltas)

    def apply_character_reply_delta(self, character_id: str) -> dict[str, float]:
        return self.apply_delta(character_id, {"happy": 1.0, "excited": 0.5})

    def apply_user_absence(self, character_id: str, hours_since_user: float, *, love: float = 50.0):
        """Legacy hourly absence bump — kept for compatibility; decay_tick covers 5-min drift."""
        if character_id not in self.states or hours_since_user < 0.5:
            return
        self.apply_decay(character_id)
        s = self.states[character_id]

        if hours_since_user >= 1:
            s.lonely = self._clamp(s.lonely + min(25.0, hours_since_user * 2.5))
        if hours_since_user >= 6:
            s.lonely = self._clamp(s.lonely + 8.0)
            s.sad = self._clamp(s.sad + min(18.0, hours_since_user * 0.8))
        if hours_since_user >= 24 and love >= 60:
            s.sad = self._clamp(s.sad + 10.0)
            s.happy = max(0.0, s.happy - min(15.0, hours_since_user * 0.3))

    def apply_effect(self, character_id: str, field: str, delta: float):
        if character_id not in self.states:
            return
        self.apply_decay(character_id)
        if hasattr(self.states[character_id], field):
            self.apply_delta(character_id, {field: delta})

    def save_snapshot(
        self,
        character_id: str,
        event_id: str | None = None,
        *,
        activity: str = "",
        delta_json: dict | None = None,
    ):
        if character_id not in self.states:
            return
        s = self.states[character_id]
        cols = self._snapshot_columns()
        delta_text = json.dumps(delta_json or {}, ensure_ascii=False)
        ts = time.time()

        if "miss_user" in cols:
            self.db.execute("""
                INSERT INTO emotion_snapshot
                (character_id, event_id, happy, calm, stressed, tired, lonely,
                 excited, embarrassed, shy, suspicious, sad, angry, fearful,
                 miss_user, jealous, activity, delta_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                character_id, event_id,
                s.happy, s.calm, s.stressed, s.tired, s.lonely,
                s.excited, s.embarrassed, s.shy, s.suspicious,
                s.sad, s.angry, s.fearful, s.miss_user, s.jealous,
                activity or "", delta_text, ts,
            ))
        else:
            self.db.execute("""
                INSERT INTO emotion_snapshot
                (character_id, event_id, happy, calm, stressed, tired, lonely,
                 excited, embarrassed, shy, suspicious, sad, angry, fearful, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                character_id, event_id,
                s.happy, s.calm, s.stressed, s.tired, s.lonely,
                s.excited, s.embarrassed, s.shy, s.suspicious,
                s.sad, s.angry, s.fearful, ts,
            ))
        self.db.commit()

    @staticmethod
    def _vector(s: EmotionState) -> dict[str, float]:
        return {key: float(getattr(s, key)) for key in EmotionState._dimensions}

    def get_summary(self, character_id: str) -> dict:
        if character_id not in self.states:
            return {}
        self.apply_decay(character_id)
        s = self.states[character_id]
        return {
            "character_id": character_id,
            "happy": round(s.happy, 1), "calm": round(s.calm, 1),
            "stressed": round(s.stressed, 1), "tired": round(s.tired, 1),
            "lonely": round(s.lonely, 1), "excited": round(s.excited, 1),
            "sad": round(s.sad, 1), "angry": round(s.angry, 1),
            "fearful": round(s.fearful, 1),
            "embarrassed": round(s.embarrassed, 1),
            "shy": round(s.shy, 1),
            "suspicious": round(s.suspicious, 1),
            "miss_user": round(s.miss_user, 1),
            "jealous": round(s.jealous, 1),
            "primary_mood": self.primary_mood(s),
        }

    def primary_mood(self, s: EmotionState) -> str:
        moods = {
            "平静": s.calm, "开心": s.happy, "疲惫": s.tired,
            "压力": s.stressed, "孤独": s.lonely, "兴奋": s.excited,
            "伤心": s.sad, "生气": s.angry, "不安": s.fearful,
            "想念": s.miss_user,
        }
        return max(moods, key=moods.get)
