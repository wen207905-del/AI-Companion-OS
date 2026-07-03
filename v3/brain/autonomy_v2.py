"""
V4 Autonomy 2.0 — 欲望驱动自主决策

替代规则触发的旧版，使用欲望 × 情绪 × 关系 × 世界 × 记忆 多维度评分。
"""

import json
from typing import Optional

# ── 欲望维度 ──
DESIRE_TYPES = [
    "desire_to_connect",    # 想联系
    "desire_to_express",    # 想表达
    "desire_to_avoid",      # 想回避
    "desire_to_comfort",    # 想寻求安慰
    "desire_to_compete",    # 竞争欲（多角色）
]

# ── 候选行为 ──
ACTION_CANDIDATES = [
    "send_message",
    "send_image",
    "write_diary",
    "stay_silent",
    "private_message_user",
    "group_interact",
    "initiate_activity",
]

# ── 最低行动阈值 ──
MIN_ACTION_THRESHOLD = 30

# ── 评分权重 ──
WEIGHTS = {
    "desire": 0.25,
    "emotion": 0.20,
    "relationship": 0.20,
    "world": 0.10,
    "memory": 0.15,
    "personality": 0.10,
}


class AutonomyV2:
    """欲望驱动的自主决策引擎 2.0。

    评分公式:
        final_score = desire*0.25 + emotion*0.20 + relationship*0.20
                    + world*0.10 + memory*0.15 + personality*0.10 - constraint
    """

    def __init__(self, db=None, event_bus=None,
                 emotion_engine=None, memory_core=None,
                 identity_state=None, social_graph=None):
        self.db = db
        self.event_bus = event_bus
        self.emotion_engine = emotion_engine
        self.memory_core = memory_core
        self.identity_state = identity_state
        self.social_graph = social_graph

        # 每角色当前欲望值
        self._desires: dict = {}  # char_id → {desire_type: value}

    # ── 欲望管理 ──

    def get_desires(self, character_id: str) -> dict:
        """获取角色当前欲望值。"""
        if character_id not in self._desires:
            self._desires[character_id] = {
                "desire_to_connect": 30,
                "desire_to_express": 20,
                "desire_to_avoid": 5,
                "desire_to_comfort": 15,
                "desire_to_compete": 5,
            }
        return dict(self._desires[character_id])

    def update_desires(self, character_id: str,
                       connect: float = 0, express: float = 0,
                       avoid: float = 0, comfort: float = 0,
                       compete: float = 0):
        """更新欲望值（增量）。"""
        d = self.get_desires(character_id)
        d["desire_to_connect"] = max(0, min(100, d["desire_to_connect"] + connect))
        d["desire_to_express"] = max(0, min(100, d["desire_to_express"] + express))
        d["desire_to_avoid"] = max(0, min(100, d["desire_to_avoid"] + avoid))
        d["desire_to_comfort"] = max(0, min(100, d["desire_to_comfort"] + comfort))
        d["desire_to_compete"] = max(0, min(100, d["desire_to_compete"] + compete))
        self._desires[character_id] = d

        # 持久化
        if self.db:
            try:
                self.db.insert_desire_snapshot(character_id, d)
            except Exception:
                pass

    # ── 决策核心 ──

    def decide(self, character_id: str,
               world_context: dict = None,
               constraint_modifiers: dict = None) -> dict:
        """为单个角色做出自主决策。

        Returns:
            {
                "character_id": str,
                "decision": "send_message" | "stay_silent" | ...,
                "score": float,
                "candidates": [...],  # 所有候选及评分
                "reasoning": str,
            }
        """
        desires = self.get_desires(character_id)

        # 获取情绪
        emotions = {}
        dominant = "calm"
        if self.emotion_engine:
            emotions = self.emotion_engine.get_emotions(character_id)
            dominant = self.emotion_engine.get_dominant_emotion(character_id)

        # 获取关系
        relationships = {}
        if self.social_graph:
            relationships = self.social_graph.get_relationships(character_id)

        # 获取记忆影响
        memory_influence = 0.0
        if self.memory_core:
            ctx = self.memory_core.retrieve_context(character_id, limit=3)
            memory_influence = min(0.3, len(ctx.get("memories", [])) * 0.1)

        # 获取人格
        personality_influence = 0.5
        attachment_score = 0.5
        if self.identity_state:
            state = self.identity_state.get_state(character_id)
            attachment_score = state.get("attachment_level", 30) / 100.0
            personality_influence = state.get("trust_level", 40) / 100.0

        # 对每个候选行为评分
        candidates = []
        for action in ACTION_CANDIDATES:
            score = self._score_action(
                action, desires, emotions, dominant,
                attachment_score, personality_influence,
                memory_influence, world_context or {},
                constraint_modifiers or {},
            )
            candidates.append({"action": action, "score": round(score, 1)})

        candidates.sort(key=lambda x: x["score"], reverse=True)
        best = candidates[0]

        # 低于阈值则静默
        if best["score"] < MIN_ACTION_THRESHOLD:
            best = {"action": "stay_silent", "score": best["score"]}

        decision = {
            "character_id": character_id,
            "decision": best["action"],
            "score": best["score"],
            "candidates": candidates[:5],
            "reasoning": self._build_reasoning(best, desires, dominant),
        }

        # 持久化决策
        if self.db:
            try:
                self.db.insert_autonomy_decision(
                    character_id, decision["decision"],
                    decision["score"], json.dumps(candidates[:5]),
                )
            except Exception:
                pass

        # 发布事件
        if self.event_bus:
            self.event_bus.publish("autonomy_decision", decision)

        return decision

    def _score_action(self, action: str, desires: dict,
                       emotions: dict, dominant: str,
                       attachment: float, personality: float,
                       memory: float, world: dict,
                       constraints: dict) -> float:
        """计算单个行为的加权评分。"""
        d_score = self._desire_score(action, desires)
        e_score = self._emotion_score(action, emotions, dominant)
        r_score = self._relationship_score(action, attachment)
        w_score = self._world_score(action, world)
        m_score = memory
        p_score = personality

        raw = (
            d_score * WEIGHTS["desire"]
            + e_score * WEIGHTS["emotion"]
            + r_score * WEIGHTS["relationship"]
            + w_score * WEIGHTS["world"]
            + m_score * WEIGHTS["memory"]
            + p_score * WEIGHTS["personality"]
        )

        # 约束惩罚
        constraint_penalty = constraints.get(action, 0)
        return max(0, raw - constraint_penalty) * 100

    def _desire_score(self, action: str, desires: dict) -> float:
        """欲望维度的评分。"""
        mapping = {
            "send_message": "desire_to_connect",
            "private_message_user": "desire_to_connect",
            "send_image": "desire_to_express",
            "write_diary": "desire_to_express",
            "initiate_activity": "desire_to_compete",
            "group_interact": "desire_to_compete",
            "stay_silent": "desire_to_avoid",
        }
        d_key = mapping.get(action)
        return desires.get(d_key, 20) / 100.0 if d_key else 0.2

    def _emotion_score(self, action: str, emotions: dict, dominant: str) -> float:
        """情绪维度评分。"""
        # 高 lonely/miss_user → 倾向联系
        if action == "send_message" or action == "private_message_user":
            return (emotions.get("lonely", 0) + emotions.get("miss_user", 0)) / 200.0
        if action == "write_diary":
            return emotions.get("sad", 0) / 100.0
        if action == "send_image":
            return emotions.get("excited", 0) / 100.0
        if action == "stay_silent":
            return emotions.get("sleepy", 0) / 100.0 + emotions.get("calm", 0) / 200.0
        if action == "group_interact":
            return emotions.get("happy", 0) / 100.0
        return 0.3

    def _relationship_score(self, action: str, attachment: float) -> float:
        """关系维度评分。"""
        if action in ("send_message", "private_message_user"):
            return attachment  # 依恋越高越想联系
        if action == "send_image":
            return attachment * 0.8
        if action == "initiate_activity":
            return attachment * 0.6
        if action == "stay_silent":
            return 1.0 - attachment  # 依恋越低越沉默
        return 0.5

    def _world_score(self, action: str, world: dict) -> float:
        """世界维度评分。"""
        time_of_day = world.get("time_of_day", "day")
        weather = world.get("weather", "clear")

        if action == "write_diary" and time_of_day == "night":
            return 0.9
        if action == "send_message" and time_of_day == "morning":
            return 0.8
        if action == "stay_silent" and time_of_day == "night":
            return 0.7
        if action == "initiate_activity" and weather == "rain":
            return 0.2
        return 0.5

    def _build_reasoning(self, best: dict, desires: dict,
                          dominant: str) -> str:
        """构建决策理由。"""
        reasons = []
        if best["action"] == "send_message":
            reasons.append(f"联系欲={desires.get('desire_to_connect', 0)}")
            reasons.append(f"主导情绪={dominant}")
        elif best["action"] == "write_diary":
            reasons.append(f"表达欲={desires.get('desire_to_express', 0)}")
        elif best["action"] == "stay_silent":
            reasons.append(f"回避欲={desires.get('desire_to_avoid', 0)}")
        reasons.append(f"得分={best['score']}")
        return "; ".join(reasons)

    # ── 批量决策 ──

    def decide_all(self, character_ids: list = None) -> list:
        """为所有角色做决策。"""
        if not character_ids and self.db:
            try:
                chars = self.db.get_all_characters()
                character_ids = [c.get("character_id") if isinstance(c, dict) else c[0]
                                 for c in (chars or [])]
            except Exception:
                return []
        return [self.decide(cid) for cid in (character_ids or [])]
