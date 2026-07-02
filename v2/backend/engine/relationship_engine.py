"""
关系引擎 V2：维度关系系统 + 阻尼增长 + 8 阶段
所有数值变化仅由事件驱动。
"""
import time
from dataclasses import dataclass, field


@dataclass
class RelationshipState:
    character_id: str
    love: float = 0
    trust: float = 0
    attachment: float = 0
    respect: float = 0
    security: float = 0
    possessiveness: float = 0
    jealousy: float = 0
    intimacy_emotional: float = 0
    intimacy_physical: float = 0

    _dimensions = [
        "love", "trust", "attachment", "respect", "security",
        "possessiveness", "jealousy", "intimacy_emotional", "intimacy_physical",
    ]

    def clamp_all(self):
        """限制所有值在 0-100 之间"""
        for attr in self._dimensions:
            setattr(self, attr, max(0.0, min(100.0, getattr(self, attr))))

    def get_stage(self) -> int:
        """根据 love 值计算关系阶段 (1-8)"""
        thresholds = [(0, 1), (16, 2), (31, 3), (51, 4), (66, 5), (81, 6), (91, 7), (96, 8)]
        stage = 1
        for threshold, s in thresholds:
            if self.love >= threshold:
                stage = s
        return stage

    def get_stage_name(self, relationship_type: str = "romance") -> str:
        if relationship_type == "brotherhood":
            names = {
                1: "陌生人", 2: "认识", 3: "朋友", 4: "损友",
                5: "铁哥们", 6: "过命兄弟", 7: "一生兄弟", 8: "亲兄弟",
            }
        else:
            names = {
                1: "陌生人", 2: "认识", 3: "朋友", 4: "暧昧",
                5: "恋人", 6: "热恋", 7: "稳定", 8: "家人",
            }
        return names.get(self.get_stage(), "陌生人")


class RelationshipEngine:
    """关系引擎：管理所有角色的关系状态"""

    def __init__(self, db_conn):
        self.db = db_conn
        self.states: dict[str, RelationshipState] = {}
        self.relationship_types: dict[str, str] = {}

    def init_character(self, character_id: str, persona: dict):
        """从角色配置初始化关系状态"""
        rel_type = persona.get("relationship_type", "romance")
        self.relationship_types[character_id] = rel_type
        intimate = persona.get("intimate_state", {})
        desire = intimate.get("desire", {})
        aff = float(intimate.get("affection", 0))
        state = RelationshipState(
            character_id=character_id,
            love=aff,
            trust=float(intimate.get("trust", aff * 0.75)),
            attachment=float(intimate.get("attachment", aff * 0.65)),
            respect=float(intimate.get("respect", 70)),
            security=float(intimate.get("security", aff * 0.7)),
            possessiveness=float(intimate.get("possessiveness", 25)),
            jealousy=float(intimate.get("jealousy", 20)),
            intimacy_emotional=float(desire.get("emotional", aff * 0.55)),
            intimacy_physical=float(desire.get("physical", aff * 0.4)),
        )
        self.states[character_id] = state

    def load_from_db(self, character_id: str) -> bool:
        """从最新快照恢复关系状态，成功返回 True"""
        if character_id not in self.states:
            return False
        cur = self.db.execute("""
            SELECT love, trust, attachment, respect, security,
                   possessiveness, jealousy, intimacy_emotional, intimacy_physical
            FROM relationship_snapshot
            WHERE character_id = ? AND COALESCE(event_id, '') != 'init'
            ORDER BY timestamp DESC, id DESC
            LIMIT 1
        """, (character_id,))
        row = cur.fetchone()
        if row is None:
            cur = self.db.execute("""
                SELECT love, trust, attachment, respect, security,
                       possessiveness, jealousy, intimacy_emotional, intimacy_physical
                FROM relationship_snapshot
                WHERE character_id = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT 1
            """, (character_id,))
            row = cur.fetchone()
        if row is None:
            return False

        s = self.states[character_id]
        s.love = float(row["love"])
        s.trust = float(row["trust"])
        s.attachment = float(row["attachment"])
        s.respect = float(row["respect"])
        s.security = float(row["security"])
        s.possessiveness = float(row["possessiveness"])
        s.jealousy = float(row["jealousy"])
        s.intimacy_emotional = float(row["intimacy_emotional"])
        s.intimacy_physical = float(row["intimacy_physical"])
        s.clamp_all()
        return True

    def damping_factor(self, current_value: float) -> float:
        """阻尼系数：值越高增长越慢"""
        if current_value < 50:
            return 1.0
        elif current_value < 70:
            return 0.7
        elif current_value < 85:
            return 0.4
        elif current_value < 95:
            return 0.15
        else:
            return 0.05

    def apply_effect(self, character_id: str, field: str, delta: float, event_id: str = ""):
        """应用事件效果，带阻尼"""
        if character_id not in self.states:
            return

        state = self.states[character_id]
        current = getattr(state, field, 0)

        # 正增长用阻尼，负增长不加阻尼（低位时甚至加速）
        if delta > 0:
            effective = delta * self.damping_factor(current)
        else:
            if current < 30:
                effective = delta * 1.3  # 低位加速
            else:
                effective = delta

        new_value = current + effective
        setattr(state, field, max(0.0, min(100.0, new_value)))
        state.clamp_all()

    def save_snapshot(self, character_id: str, event_id: str):
        """保存关系快照到数据库"""
        if character_id not in self.states:
            return
        s = self.states[character_id]
        self.db.execute("""
            INSERT INTO relationship_snapshot
            (character_id, event_id, love, trust, attachment, respect, security,
             possessiveness, jealousy, intimacy_emotional, intimacy_physical, stage, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            character_id, event_id,
            s.love, s.trust, s.attachment, s.respect,
            s.security, s.possessiveness, s.jealousy,
            s.intimacy_emotional, s.intimacy_physical,
            s.get_stage(), time.time(),
        ))
        self.db.commit()

    def get_summary(self, character_id: str) -> dict:
        """获取角色关系摘要"""
        if character_id not in self.states:
            return {}
        s = self.states[character_id]
        rel_type = self.relationship_types.get(character_id, "romance")
        return {
            "character_id": character_id,
            "stage": s.get_stage(),
            "stage_name": s.get_stage_name(rel_type),
            "relationship_type": rel_type,
            "love": round(s.love, 1),
            "trust": round(s.trust, 1),
            "attachment": round(s.attachment, 1),
            "respect": round(s.respect, 1),
            "security": round(s.security, 1),
            "possessiveness": round(s.possessiveness, 1),
            "jealousy": round(s.jealousy, 1),
            "intimacy_emotional": round(s.intimacy_emotional, 1),
            "intimacy_physical": round(s.intimacy_physical, 1),
        }

    def ensure_minimum_love(self, min_love: float = 70.0, event_id: str = "love_floor") -> list[str]:
        """将低于 min_love 的角色好感提升到 min_love，返回被调整的角色 id 列表。"""
        updated: list[str] = []
        floor = float(min_love)
        for character_id, s in self.states.items():
            if s.love >= floor:
                continue
            s.love = floor
            s.clamp_all()
            self.save_snapshot(character_id, event_id)
            updated.append(character_id)
        return updated
