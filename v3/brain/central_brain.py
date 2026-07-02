"""
中央意识层 — Phase 2 完整实现

Converge 多引擎输出为统一角色状态。
仲裁规则：
    sleepiness > 80 → override silence
    jealousy > 70 → override emotional message only
    loneliness + attachment high → boost proactive
"""

from ..config import PHASE2_SCENE_OVERRIDES
from .scene_classifier import SceneClassifier
from .state_arbiter import StateArbiter


class CentralBrain:
    """中央意识层 — 收敛多引擎输出为统一状态。

    输入 Autonomy Engine 的初步决策及各引擎原始状态，
    通过 SceneClassifier 分类场景 + StateArbiter 冲突仲裁，
    输出唯一角色状态和行为许可。
    """

    def __init__(self):
        self.scene_classifier = SceneClassifier()
        self.state_arbiter = StateArbiter()

    def converge(self, engine_states: dict, world_state,
                 autonomy_decision: dict = None) -> dict:
        """收敛多引擎状态为统一角色状态。

        Args:
            engine_states: {"emotion": {...}, "relationship": {...}, "mood_pressure": {...}}
            world_state: WorldState 对象
            autonomy_decision: Autonomy Engine 的决策（可选）

        Returns:
            {
                "final_emotion":       str,
                "allowed_actions":     list,
                "blocked_actions":     list,
                "tone":               str,
                "scene":              dict,
                "arbitration":        dict,
                "override_silence":   bool,
                "override_emotional": bool,
                "boost_proactive":    bool,
            }
        """
        emotion_state = engine_states.get("emotion", {})
        mood_bias = engine_states.get("mood_bias", "")

        # 1. 场景分类
        scene = self.scene_classifier.classify(world_state, emotion_state, mood_bias)

        # 2. 场景级 Central Brain 覆写
        scene_override = self.scene_classifier.get_scene_override(
            scene.get("scene_key", ""))
        if scene_override:
            # 场景级覆盖直接生效
            return self._apply_scene_override(scene_override, scene)

        # 3. 状态仲裁
        arbitration = self.state_arbiter.resolve(engine_states)

        # 4. 计算 allowed / blocked
        actions = self.state_arbiter.get_allowed_actions(arbitration)

        # 5. 与 Autonomy 决策融合
        if autonomy_decision and autonomy_decision.get("should_act"):
            auto_type = autonomy_decision["action_type"]
            # 如果仲裁阻止了该行为，降级为 SILENCE
            if auto_type in actions.get("blocked_actions", []):
                return {
                    "final_emotion":      arbitration["primary_emotion"],
                    "allowed_actions":    [],
                    "blocked_actions":    list(actions["blocked_actions"]),
                    "tone":              arbitration["tone"],
                    "scene":             scene,
                    "arbitration":       arbitration,
                    "override_silence":  True,
                    "override_emotional":False,
                    "boost_proactive":   False,
                }

        # 6. 如果仲裁要求 boost_proactive，提升 score
        if arbitration.get("boost_proactive") and autonomy_decision:
            autonomy_decision["_boosted"] = True

        return {
            "final_emotion":      arbitration["primary_emotion"],
            "allowed_actions":    actions["allowed_actions"],
            "blocked_actions":    actions["blocked_actions"],
            "tone":              arbitration["tone"],
            "scene":             scene,
            "arbitration":       arbitration,
            "override_silence":  arbitration.get("override_silence", False),
            "override_emotional":arbitration.get("override_emotional", False),
            "boost_proactive":   arbitration.get("boost_proactive", False),
        }

    def _apply_scene_override(self, scene_override: dict, scene: dict) -> dict:
        """应用场景级覆写规则。"""
        return {
            "final_emotion":      scene_override.get("emotion", scene["dominant_mood"]),
            "allowed_actions":    scene_override.get("allowed_actions", []),
            "blocked_actions":    scene_override.get("blocked_actions", []),
            "tone":              scene_override.get("tone", "gentle"),
            "scene":             scene,
            "arbitration":       {"rule_applied": "scene_override"},
            "override_silence":  scene_override.get("override_silence", False),
            "override_emotional":scene_override.get("override_emotional", False),
            "boost_proactive":   scene_override.get("boost_proactive", False),
        }
