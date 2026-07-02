"""
自主行为引擎 — 候选行为评分模式（P2 重写）

核心改动：
  旧：单一阈值判定（score → 一个 action）
  新：多候选行为并行评分 → 选最高分

候选行为：
  send_message / write_diary / send_image / stay_silent / group_interact

每个候选计算 6 维分数：
  desire_score   — 角色内在驱动力（情绪压力、个性主动性）
  emotion_score  — 当前情绪适配度
  relationship_score — 关系状态适配度
  world_score    — 世界状态适配度（时间/天气/场景）
  memory_score   — 记忆触发适配度
  constraint_score — 约束条件（冷却、场景禁止）

总分数加权求和后选最高分，低于阈值则 stay_silent。
保留原有阈值判定作为兜底模式。
"""

import random
from typing import Optional

from ..config import (
    PHASE2_THRESHOLD_RANGES, PHASE2_ACTION_PRIORITY,
    PHASE2_ACTION_COOLDOWNS,
)
from .decision_factors import DecisionFactors
from .action_policy import ActionPolicy


class AutonomyEngine:
    """自主行为引擎 — 候选行为评分模式。

    评估角色是否主动行动，对多个候选行为并行评分，
    选最高分执行，实现更细腻的行为选择。
    """

    # 候选行为定义
    CANDIDATE_ACTIONS = [
        "send_message",
        "write_diary",
        "send_image",
        "group_interact",
        "stay_silent",
    ]

    # 各候选行为的 6 维权重配置
    # 权重总和归一化，每类行为有不同的侧重点
    CANDIDATE_WEIGHTS = {
        "send_message": {
            "desire": 0.25, "emotion": 0.25, "relationship": 0.20,
            "world": 0.15, "memory": 0.10, "constraint": 0.05,
        },
        "write_diary": {
            "desire": 0.15, "emotion": 0.30, "relationship": 0.05,
            "world": 0.20, "memory": 0.25, "constraint": 0.05,
        },
        "send_image": {
            "desire": 0.20, "emotion": 0.25, "relationship": 0.20,
            "world": 0.20, "memory": 0.10, "constraint": 0.05,
        },
        "group_interact": {
            "desire": 0.15, "emotion": 0.15, "relationship": 0.15,
            "world": 0.25, "memory": 0.15, "constraint": 0.15,
        },
        "stay_silent": {
            "desire": 0.10, "emotion": 0.10, "relationship": 0.10,
            "world": 0.10, "memory": 0.10, "constraint": 0.50,
        },
    }

    # 行为触发最低阈值（低于此分数强制 silence）
    MIN_ACTION_THRESHOLD = 30.0

    # 行为到 action_type 的映射
    ACTION_TYPE_MAP = {
        "send_message": "SEND_MESSAGE",
        "write_diary": "WRITE_DIARY",
        "send_image": "SEND_IMAGE",
        "group_interact": "GROUP_INTERACTION",
        "stay_silent": "SILENCE",
    }

    def __init__(self):
        self.decision_factors = DecisionFactors()
        self.action_policy = ActionPolicy()
        self.mood_pressure = None
        self.absence_system = None
        self.feedback_loop = None
        self.central_brain = None

    def evaluate(self, character_id: str, world_state,
                 emotion_state: dict, relationship_state: dict,
                 personality: dict, user_activity: dict,
                 memory_context: dict = None) -> dict:
        """评估角色自主行为 — 候选评分模式。

        Returns:
            {action_type, target, intent, confidence, priority,
             should_act, score, candidate_scores, reason}
        """
        memory_context = memory_context or {}

        # 1. 收集因子（供所有候选共用）
        factors = self.decision_factors.collect_all_factors(
            character_id, world_state, emotion_state, relationship_state,
            personality, user_activity, memory_context)

        if self.mood_pressure or self.absence_system:
            factors = self.decision_factors.inject_external(
                factors, character_id,
                mood_pressure=self.mood_pressure,
                absence_system=self.absence_system)

        raw_scores = factors["raw_scores"]

        # 2. 并行计算所有候选行为的综合评分
        candidate_scores = self._score_all_candidates(
            character_id, factors, raw_scores, world_state)

        # 3. 选出最高分候选
        best_candidate = max(candidate_scores, key=lambda c: c["total_score"])
        best_total = best_candidate["total_score"]

        # 4. 阈值兜底：最高分低于阈值 → silence
        if best_total < self.MIN_ACTION_THRESHOLD:
            best_candidate = {
                "action": "stay_silent",
                "total_score": 0.0,
                "scores": {"desire": 0, "emotion": 0, "relationship": 0,
                           "world": 0, "memory": 0, "constraint": 100},
            }

        action_type = self.ACTION_TYPE_MAP.get(best_candidate["action"], "SILENCE")
        should_act = action_type != "SILENCE"

        # 5. 冷却过滤
        ts = world_state.dt.timestamp() if hasattr(world_state, "dt") and world_state.dt else 0
        if should_act and not self.action_policy.is_action_allowed(character_id, action_type, ts):
            action_type = "SILENCE"
            should_act = False
            best_candidate = {
                "action": "stay_silent",
                "total_score": 0.0,
                "scores": {"desire": 0, "emotion": 0, "relationship": 0,
                           "world": 0, "memory": 0, "constraint": 100},
            }

        # 6. 兜底：阈值判定（当候选评分结果不理想时）
        if action_type == "SILENCE":
            fallback_score = self.decision_factors.compute_score(raw_scores)
            if fallback_score >= 30:
                fb_action, fb_intent = self._threshold_decide(fallback_score, raw_scores)
                if fb_action != "SILENCE":
                    action_type = fb_action
                    should_act = True

        confidence = min(best_total / 100.0, 1.0)
        priority = PHASE2_ACTION_PRIORITY.get(action_type, 0)

        decision = {
            "action_type": action_type,
            "target": self._infer_target(action_type),
            "intent": best_candidate.get("intent", self._infer_intent(raw_scores)),
            "confidence": round(confidence, 3),
            "priority": priority,
            "should_act": should_act,
            "score": round(best_total, 2),
            "raw_scores": raw_scores,
            "candidate_scores": [
                {"action": c["action"], "total": round(c["total_score"], 2)}
                for c in candidate_scores
            ],
            "reason": self._reason(best_total, action_type, raw_scores),
        }

        if should_act:
            self.action_policy.record_action(character_id, action_type, ts)

        return decision

    # ── 候选评分 ──

    def _score_all_candidates(self, character_id: str, factors: dict,
                               raw_scores: dict, world_state) -> list:
        """对所有候选行为并行评分。"""
        results = []
        for action in self.CANDIDATE_ACTIONS:
            scores = self._score_candidate(action, character_id, factors,
                                           raw_scores, world_state)
            weights = self.CANDIDATE_WEIGHTS.get(action, {})
            total = sum(
                scores[k] * weights.get(k, 0.0)
                for k in ["desire", "emotion", "relationship", "world", "memory", "constraint"]
            )
            results.append({
                "action": action,
                "total_score": total,
                "scores": scores,
            })
        return results

    def _score_candidate(self, action: str, character_id: str,
                          factors: dict, raw_scores: dict, world_state) -> dict:
        """计算单个候选行为的 6 维分数 [0-100]。"""
        rs = raw_scores

        # desire_score — 内在驱动力
        desire = self._calc_desire_score(action, rs, factors)

        # emotion_score — 情绪适配
        emotion = self._calc_emotion_score(action, rs, factors)

        # relationship_score — 关系适配
        relationship = self._calc_relationship_score(action, rs, factors)

        # world_score — 世界状态适配
        world = self._calc_world_score(action, rs, factors, world_state)

        # memory_score — 记忆触发
        memory = self._calc_memory_score(action, rs, factors)

        # constraint_score — 约束（冷却、场景禁止）100 = 无约束, 0 = 完全禁止
        constraint = self._calc_constraint_score(action, character_id, world_state)

        return {
            "desire": desire, "emotion": emotion, "relationship": relationship,
            "world": world, "memory": memory, "constraint": constraint,
        }

    def _calc_desire_score(self, action: str, rs: dict, factors: dict) -> float:
        """内在驱动力分数。"""
        lonely = rs.get("emotion_lonely", 0)
        initiative = rs.get("personality_initiative", 0)
        inactive = rs.get("user_inactive_time", 0)

        base = 30.0

        if action == "send_message":
            base += lonely * 0.4 + inactive * 0.3 + initiative * 0.3
        elif action == "write_diary":
            base += lonely * 0.5 + initiative * 0.3
        elif action == "send_image":
            base += lonely * 0.35 + inactive * 0.25 + initiative * 0.2
        elif action == "group_interact":
            base += initiative * 0.5 + lonely * 0.2
        elif action == "stay_silent":
            return 10.0

        return min(base, 100.0)

    def _calc_emotion_score(self, action: str, rs: dict, factors: dict) -> float:
        """情绪适配分数。"""
        lonely = rs.get("emotion_lonely", 0)
        emo = factors.get("emotion", {})

        if action == "send_message":
            return min(30 + lonely * 0.5 + emo.get("happy", 0) * 0.3, 100.0)
        elif action == "write_diary":
            return min(30 + lonely * 0.4 + emo.get("calm", 0) * 0.3
                       + emo.get("sad", 0) * 0.3, 100.0)
        elif action == "send_image":
            return min(25 + lonely * 0.4 + emo.get("happy", 0) * 0.3, 100.0)
        elif action == "group_interact":
            return min(30 + emo.get("happy", 0) * 0.5 + lonely * 0.2, 100.0)
        else:
            return 10.0

    def _calc_relationship_score(self, action: str, rs: dict, factors: dict) -> float:
        """关系适配分数。"""
        attachment = rs.get("relationship_attachment", 0)
        rel = factors.get("relationship", {})

        if action == "send_message":
            return min(30 + attachment * 0.5 + rel.get("trust", 0) * 0.2, 100.0)
        elif action == "send_image":
            return min(25 + attachment * 0.6 + rel.get("love", 0) * 0.3, 100.0)
        elif action == "group_interact":
            return min(30 + rel.get("trust", 0) * 0.4 + attachment * 0.3, 100.0)
        elif action == "write_diary":
            return 20.0  # 日记与关系弱相关
        else:
            return 10.0

    def _calc_world_score(self, action: str, rs: dict, factors: dict,
                           world_state) -> float:
        """世界状态适配分数。"""
        night = rs.get("world_night_factor", 0)
        wld = factors.get("world", {})

        if action == "send_message":
            # 深夜降低消息倾向
            if night > 70:
                return max(10.0, 50.0 - (night - 70) * 0.5)
            return 50.0 + (100 - night) * 0.3
        elif action == "write_diary":
            # 深夜 + 安静场景 → 日记倾向高
            return min(30 + night * 0.5 + (100 - wld.get("weather_lonely", 50)) * 0.2, 100.0)
        elif action == "send_image":
            return min(30 + (100 - night) * 0.3, 100.0)
        elif action == "group_interact":
            # 深夜禁止群互动
            if night > 70:
                return 5.0
            return 40.0
        else:
            return 10.0

    def _calc_memory_score(self, action: str, rs: dict, factors: dict) -> float:
        """记忆触发分数。"""
        triggers = rs.get("memory_triggers", 0)
        mem = factors.get("memory", {})

        if action == "write_diary":
            return min(30 + triggers * 0.5 + mem.get("triggers", 0) * 0.3, 100.0)
        elif action == "send_message":
            return min(25 + triggers * 0.4, 100.0)
        elif action == "group_interact":
            return min(20 + triggers * 0.3, 100.0)
        elif action == "send_image":
            return min(15 + triggers * 0.3, 100.0)
        else:
            return 10.0

    def _calc_constraint_score(self, action: str, character_id: str,
                                world_state) -> float:
        """约束分数 — 100 无约束，0 完全禁止。"""
        score = 100.0

        # 冷却惩罚：使用 is_on_cooldown + get_cooldown_remaining 计算
        if self.action_policy and action != "stay_silent":
            at = self.ACTION_TYPE_MAP.get(action, "")
            ts = world_state.dt.timestamp() if hasattr(world_state, "dt") and world_state.dt else 0
            if self.action_policy.is_on_cooldown(character_id, at, ts):
                remaining = self.action_policy.get_cooldown_remaining(character_id, at, ts)
                cooldown = PHASE2_ACTION_COOLDOWNS.get(at, 0)
                if cooldown > 0:
                    score = min(score, max(0.0, (1.0 - remaining / cooldown) * 100.0))

        # 场景禁止检查
        if action in ("send_image", "group_interact"):
            tp = getattr(world_state, "time_period", "morning")
            if tp in ("late_night", "night"):
                score = min(score, 20.0)

        return score

    # ── 兜底：阈值判定 ──

    def _threshold_decide(self, score: float, raw_scores: dict) -> tuple:
        """阈值判定 → (action_type, intent)。兜底使用。"""
        for name, rng in PHASE2_THRESHOLD_RANGES.items():
            if rng["min"] <= score < rng["max"]:
                if name == "silence":
                    return ("SILENCE", "none")
                elif name == "low_chance_message":
                    if random.random() < rng.get("probability", 0.3):
                        return ("SEND_MESSAGE", self._infer_intent(raw_scores))
                    return ("SILENCE", "low_probability")
                elif name == "message_or_diary":
                    if raw_scores.get("world_night_factor", 0) > 70 and \
                       raw_scores.get("emotion_lonely", 0) > 50:
                        return ("WRITE_DIARY", "reflect")
                    return ("SEND_MESSAGE", self._infer_intent(raw_scores))
                elif name == "message_with_image":
                    return ("SEND_MESSAGE", self._infer_intent(raw_scores))
                elif name == "proactive_event":
                    if raw_scores.get("relationship_attachment", 0) > 70:
                        return ("RELATIONSHIP_EVENT", "emotional")
                    return ("GROUP_INTERACTION", "social")
        return ("SILENCE", "none")

    # ── 辅助方法 ──

    def _infer_intent(self, rs: dict) -> str:
        triggers = rs.get("memory_triggers", 0)
        lonely = rs.get("emotion_lonely", 0)
        inactive = rs.get("user_inactive_time", 0)
        attachment = rs.get("relationship_attachment", 0)
        if triggers > 60: return "memory"
        if lonely > 70 and inactive > 50: return "miss_you"
        if attachment > 70: return "emotional"
        if inactive > 40: return "chat"
        return "share"

    def _infer_target(self, at: str) -> str:
        return {
            "SEND_MESSAGE": "user", "SEND_IMAGE": "user",
            "WRITE_DIARY": "self", "UPDATE_MEMORY": "self",
            "RELATIONSHIP_EVENT": "user",
            "GROUP_INTERACTION": "group", "SILENCE": "self",
        }.get(at, "self")

    def _reason(self, score: float, at: str, rs: dict) -> str:
        parts = [f"score={score:.1f}"]
        if rs.get("emotion_lonely", 0) > 50: parts.append("lonely_high")
        if rs.get("user_inactive_time", 0) > 40: parts.append("user_inactive")
        if rs.get("world_night_factor", 0) > 60: parts.append("nighttime")
        if at == "SILENCE": parts.append("below_threshold")
        return ", ".join(parts)

    # ── 执行 ──

    def execute_decision(self, character_id: str, decision: dict,
                          context: dict = None) -> dict:
        """执行自主行为决策 — 走 ActionDispatcher 统一出口。"""
        at = decision["action_type"]
        if at == "SILENCE":
            return {"success": True, "action": "SILENCE", "status": "no_action"}

        result = self.action_dispatcher.dispatch(
            character_id, at, context or {})

        if self.feedback_loop:
            self.feedback_loop.on_action_done(
                character_id, at, decision, result)

        return result
