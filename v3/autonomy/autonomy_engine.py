"""
自主行为引擎 — Phase 2 完整实现

评分模型：
    score = emotion.lonely*0.25 + relationship.attachment*0.2
          + world.night_factor*0.15 + user.inactive_time*0.2
          + personality.initiative*0.1 + memory.triggers*0.1

阈值判定：
    score < 30   → SILENCE
    30-60        → SEND_MESSAGE（低概率 30%）
    60-80        → SEND_MESSAGE | WRITE_DIARY
    80-90        → SEND_MESSAGE + SEND_IMAGE
    90+          → RELATIONSHIP_EVENT | GROUP_INTERACTION

输出：{action_type, target, intent, confidence, priority}
"""

import random
from ..config import PHASE2_THRESHOLD_RANGES, PHASE2_ACTION_PRIORITY
from .decision_factors import DecisionFactors
from .action_policy import ActionPolicy
from .action_dispatcher import ActionDispatcher


class AutonomyEngine:
    """自主行为引擎 — Phase 2 核心。

    评估角色是否主动行动，决定行动类型并调度执行。
    """

    def __init__(self):
        self.decision_factors = DecisionFactors()
        self.action_policy = ActionPolicy()
        self.action_dispatcher = ActionDispatcher()
        self.mood_pressure = None
        self.absence_system = None
        self.feedback_loop = None

    def evaluate(self, character_id: str, world_state,
                 emotion_state: dict, relationship_state: dict,
                 personality: dict, user_activity: dict,
                 memory_context: dict = None) -> dict:
        """评估角色自主行为。

        Returns:
            {action_type, target, intent, confidence, priority, should_act, score, raw_scores, reason}
        """
        # 1. 收集因子
        factors = self.decision_factors.collect_all_factors(
            character_id, world_state, emotion_state, relationship_state,
            personality, user_activity, memory_context or {})
        if self.mood_pressure or self.absence_system:
            factors = self.decision_factors.inject_external(
                factors, character_id,
                mood_pressure=self.mood_pressure, absence_system=self.absence_system)

        raw_scores = factors["raw_scores"]
        score = self.decision_factors.compute_score(raw_scores)

        # 2. 阈值判定
        action_type, intent = self._threshold_decide(score, raw_scores)

        # 3. 冷却过滤
        ts = world_state.dt.timestamp() if world_state.dt else 0
        if not self.action_policy.is_action_allowed(character_id, action_type, ts):
            action_type = "SILENCE"
            intent = "cooldown"

        should_act = action_type != "SILENCE"
        confidence = min(score / 100.0, 1.0)
        priority = PHASE2_ACTION_PRIORITY.get(action_type, 0)

        decision = {
            "action_type": action_type,
            "target": self._infer_target(action_type),
            "intent": intent,
            "confidence": round(confidence, 3),
            "priority": priority,
            "should_act": should_act,
            "score": round(score, 2),
            "raw_scores": raw_scores,
            "reason": self._reason(score, action_type, raw_scores),
        }
        if should_act:
            self.action_policy.record_action(character_id, action_type, ts)
        return decision

    def _threshold_decide(self, score: float, raw_scores: dict) -> tuple:
        """阈值判定 → (action_type, intent)."""
        for name, rng in PHASE2_THRESHOLD_RANGES.items():
            if rng["min"] <= score < rng["max"]:
                if name == "silence":
                    return ("SILENCE", "none")
                elif name == "low_chance_message":
                    if random.random() < rng.get("probability", 0.3):
                        return ("SEND_MESSAGE", self._infer_intent(raw_scores))
                    return ("SILENCE", "low_probability")
                elif name == "message_or_diary":
                    if raw_scores.get("world_night_factor", 0) > 70 and raw_scores.get("emotion_lonely", 0) > 50:
                        return ("WRITE_DIARY", "reflect")
                    return ("SEND_MESSAGE", self._infer_intent(raw_scores))
                elif name == "message_with_image":
                    return ("SEND_MESSAGE", self._infer_intent(raw_scores))
                elif name == "proactive_event":
                    if raw_scores.get("relationship_attachment", 0) > 70:
                        return ("RELATIONSHIP_EVENT", "emotional")
                    return ("GROUP_INTERACTION", "social")
        return ("SILENCE", "none")

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
        return {"SEND_MESSAGE":"user","SEND_IMAGE":"user","WRITE_DIARY":"self",
                "UPDATE_MEMORY":"self","RELATIONSHIP_EVENT":"user",
                "GROUP_INTERACTION":"group","SILENCE":"self"}.get(at, "self")

    def _reason(self, score, at, rs):
        parts = [f"score={score:.1f}"]
        if rs.get("emotion_lonely", 0) > 50: parts.append("lonely_high")
        if rs.get("user_inactive_time", 0) > 40: parts.append("user_inactive")
        if rs.get("world_night_factor", 0) > 60: parts.append("nighttime")
        return ", ".join(parts)

    def execute_decision(self, character_id: str, decision: dict, context: dict = None) -> dict:
        """执行自主行为决策。"""
        at = decision["action_type"]
        if at == "SILENCE":
            return {"success": True, "action": "SILENCE", "status": "no_action"}
        result = self.action_dispatcher.dispatch(character_id, at, context or {})
        if at == "SEND_MESSAGE" and decision.get("score", 0) >= 80:
            img_result = self.action_dispatcher.dispatch(character_id, "SEND_IMAGE", context or {})
            result["attached_image"] = img_result
        if self.feedback_loop:
            self.feedback_loop.on_action_done(character_id, at, decision, result)
        return result

    def calculate_action_probability(self, factors: dict) -> float:
        return self.decision_factors.compute_score(factors.get("raw_scores", {})) / 100.0

    def select_action(self, allowed: list, prob: float) -> str:
        if prob < 0.3: return "SILENCE"
        return allowed[0] if allowed else "SILENCE"
