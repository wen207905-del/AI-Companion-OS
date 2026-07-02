"""
Memory Influence — 记忆影响决策计算

记忆不只是存储，而是参与行为决策。
例如：
  - "用户曾冷落我" → 主动联系概率调整
  - "曾经被温柔安慰" → trust +5
  - "上次发图没回应" → send_image 阈值提高
"""

from typing import Optional


class MemoryInfluence:
    """记忆影响计算器 — 记忆驱动的行为偏差。"""

    # 记忆关键词 → 行为偏差映射
    INFLUENCE_RULES = {
        "user_cold": {
            "lonely": 10,
            "initiative_probability": 0.15,      # 主动联系概率 +15%
            "send_image_threshold": 0.10,        # 发图阈值 +10%（更不愿发）
            "chat_warmth": -0.1,                  # 回复温暖度 -10%
        },
        "user_warm": {
            "trust": 5,
            "attachment": 3,
            "initiative_probability": 0.05,
            "chat_warmth": 0.1,
        },
        "ignored_message": {
            "initiative_probability": -0.10,     # 被无视 → 下次主动意愿降低
            "send_image_threshold": 0.15,
            "lonely": 5,
        },
        "received_compliment": {
            "happy": 8,
            "shy": 10,
            "trust": 2,
            "chat_warmth": 0.1,
        },
        "shared_secret": {
            "trust": 8,
            "attachment": 5,
            "intimacy_factor": 0.1,
        },
        "festival_together": {
            "attachment": 5,
            "happy": 5,
            "initiative_probability": 0.1,
        },
    }

    def __init__(self, db=None):
        self.db = db

    def calculate_influence(self, character_id: str,
                             recent_memories: list = None) -> dict:
        """计算记忆对当前行为的影响。

        Returns:
            {
                emotion_delta: {dim: delta, ...},
                behavior_modifiers: {
                    initiative_probability: float,
                    send_image_threshold: float,
                    chat_warmth: float,
                    trust_delta: float,
                    attachment_delta: float,
                }
            }
        """
        influence = {
            "emotion_delta": {},
            "behavior_modifiers": {
                "initiative_probability": 0.0,
                "send_image_threshold": 0.0,
                "chat_warmth": 0.0,
                "trust_delta": 0.0,
                "attachment_delta": 0.0,
            },
        }

        if not recent_memories:
            return influence

        # 扫描近期记忆，匹配影响规则
        for mem in recent_memories:
            content = (mem.get("content", "") + " " + mem.get("summary", "")).lower()

            for pattern, effects in self.INFLUENCE_RULES.items():
                if pattern in content:
                    # 情感影响
                    for dim in ["lonely", "happy", "shy", "trust", "attachment"]:
                        if dim in effects:
                            influence["emotion_delta"].setdefault(dim, 0)
                            influence["emotion_delta"][dim] += effects[dim]

                    # 行为修饰
                    for key in ["initiative_probability", "send_image_threshold", "chat_warmth"]:
                        if key in effects:
                            influence["behavior_modifiers"][key] += effects[key]

                    # 信任/依恋
                    if "trust" in effects:
                        influence["behavior_modifiers"]["trust_delta"] += effects["trust"]
                    if "attachment" in effects:
                        influence["behavior_modifiers"]["attachment_delta"] += effects["attachment"]

        # 限制范围
        for key in influence["behavior_modifiers"]:
            influence["behavior_modifiers"][key] = max(-0.5, min(0.5,
                influence["behavior_modifiers"][key]))

        return influence

    def get_initiative_modifier(self, character_id: str) -> float:
        """获取主动联系概率修正值。"""
        influence = self.calculate_influence(character_id)
        return influence["behavior_modifiers"].get("initiative_probability", 0.0)
