"""
情绪引擎 V2：实时情绪系统，支持自然衰减。"""
import time
from dataclasses import dataclass


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
    last_update: float = 0.0

    _dimensions = [
        "happy", "calm", "stressed", "tired", "lonely", "excited",
        "embarrassed", "shy", "suspicious", "sad", "angry", "fearful",
    ]


class EmotionEngine:
    """情绪引擎：管理实时情绪 + 自然衰减"""

    DECAY_RATES = {
        "happy": 2, "excited": 5, "stressed": 3, "angry": 4,
        "sad": 3, "fearful": 3, "embarrassed": 4, "shy": 2,
        "suspicious": 2, "lonely": 1, "tired": 3,
    }

    def __init__(self, db_conn):
        self.db = db_conn
        self.states: dict[str, EmotionState] = {}

    def init_character(self, character_id: str):
        self.states[character_id] = EmotionState(
            character_id=character_id,
            last_update=time.time()
        )

    def load_from_db(self, character_id: str) -> bool:
        """从最新快照恢复情绪状态，成功返回 True"""
        if character_id not in self.states:
            return False
        cur = self.db.execute("""
            SELECT happy, calm, stressed, tired, lonely, excited,
                   embarrassed, shy, suspicious, sad, angry, fearful, timestamp
            FROM emotion_snapshot
            WHERE character_id = ? AND COALESCE(event_id, '') != 'init'
            ORDER BY timestamp DESC, id DESC
            LIMIT 1
        """, (character_id,))
        row = cur.fetchone()
        if row is None:
            cur = self.db.execute("""
                SELECT happy, calm, stressed, tired, lonely, excited,
                       embarrassed, shy, suspicious, sad, angry, fearful, timestamp
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
        s.last_update = float(row["timestamp"])
        return True

    def apply_decay(self, character_id: str):
        """应用自然衰减"""
        if character_id not in self.states:
            return
        s = self.states[character_id]
        now = time.time()
        hours = max(0, (now - s.last_update) / 3600)
        if hours < 0.01:  # 小于 36 秒不衰减
            return

        for field, rate in self.DECAY_RATES.items():
            current = getattr(s, field)
            if current > 0:
                decay = rate * hours
                setattr(s, field, max(0, current - decay))
        s.last_update = now

    def apply_effect(self, character_id: str, field: str, delta: float):
        """应用情绪变化"""
        if character_id not in self.states:
            return
        s = self.states[character_id]
        self.apply_decay(character_id)

        if hasattr(s, field):
            current = getattr(s, field)
            setattr(s, field, max(0.0, min(100.0, current + delta)))

    def save_snapshot(self, character_id: str, event_id: str = None):
        """保存情绪快照"""
        if character_id not in self.states:
            return
        s = self.states[character_id]
        self.db.execute("""
            INSERT INTO emotion_snapshot
            (character_id, event_id, happy, calm, stressed, tired, lonely,
             excited, embarrassed, shy, suspicious, sad, angry, fearful, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            character_id, event_id,
            s.happy, s.calm, s.stressed, s.tired, s.lonely,
            s.excited, s.embarrassed, s.shy, s.suspicious,
            s.sad, s.angry, s.fearful, time.time(),
        ))
        self.db.commit()

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
            "primary_mood": self.primary_mood(s),
        }

    def primary_mood(self, s: EmotionState) -> str:
        """计算主导情绪"""
        moods = {
            "平静": s.calm, "开心": s.happy, "疲惫": s.tired,
            "压力": s.stressed, "孤独": s.lonely, "兴奋": s.excited,
            "伤心": s.sad, "生气": s.angry, "不安": s.fearful,
        }
        return max(moods, key=moods.get)
