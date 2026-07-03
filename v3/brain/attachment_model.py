"""
V4 Attachment Model — 依恋系统

四种依恋风格：secure / anxious / avoidant / fearful。
每个角色可配置风格，影响主动联系频率、吃醋阈值、回避行为。
"""

import random
from datetime import datetime, timedelta
from typing import Optional

# ── 依恋风格定义 ──
ATTACHMENT_STYLES = ["secure", "anxious", "avoidant", "fearful"]

# ── 风格配置 ──
STYLE_PROFILES = {
    "secure": {
        "contact_frequency": 0.5,      # 主动联系频率倍率
        "jealousy_threshold": 80,       # 吃醋阈值（高=不容易吃醋）
        "avoidance_tendency": 0.05,     # 回避倾向
        "intimacy_growth": 1.2,         # 亲密度增长率
        "trust_growth": 1.3,            # 信任增长率
        "decay_resistance": 0.8,        # 依恋衰减抵抗（低=衰减慢）
    },
    "anxious": {
        "contact_frequency": 1.8,
        "jealousy_threshold": 35,
        "avoidance_tendency": 0.02,
        "intimacy_growth": 1.6,
        "trust_growth": 0.7,
        "decay_resistance": 0.3,
    },
    "avoidant": {
        "contact_frequency": 0.2,
        "jealousy_threshold": 70,
        "avoidance_tendency": 0.35,
        "intimacy_growth": 0.4,
        "trust_growth": 0.5,
        "decay_resistance": 1.2,
    },
    "fearful": {
        "contact_frequency": 0.6,
        "jealousy_threshold": 45,
        "avoidance_tendency": 0.25,
        "intimacy_growth": 0.6,
        "trust_growth": 0.4,
        "decay_resistance": 0.9,
    },
}


class AttachmentModel:
    """依恋系统。

    管理角色依恋状态，影响行为倾向。
    """

    def __init__(self, db=None, event_bus=None):
        self.db = db
        self.event_bus = event_bus

        # char_id → style config
        self._styles: dict = {}  # char_id → attachment_style
        self._states: dict = {}  # char_id → {attachment_level, trust_level, ...}
        self._contact_cooldown: dict = {}  # char_id → datetime (下次可主动联系)

    # ── 风格配置 ──

    def set_style(self, character_id: str, style: str):
        """配置依恋风格。"""
        if style not in ATTACHMENT_STYLES:
            raise ValueError(f"未知依恋风格: {style}，可选: {ATTACHMENT_STYLES}")
        self._styles[character_id] = style
        self._states[character_id] = {
            "attachment_level": 30.0,
            "trust_level": 40.0,
            "jealousy_level": 0.0,
            "last_interaction": datetime.now(),
        }
        if self.db:
            try:
                self.db.upsert_attachment_state(character_id, style,
                                                 self._states[character_id])
            except Exception:
                pass

    def get_style(self, character_id: str) -> str:
        """获取当前风格。"""
        return self._styles.get(character_id, "secure")

    def get_profile(self, character_id: str) -> dict:
        """获取风格配置。"""
        return STYLE_PROFILES.get(self.get_style(character_id), STYLE_PROFILES["secure"])

    # ── 互动影响 ──

    def on_interaction(self, character_id: str, 
                        positive: bool = True,
                        intensity: float = 0.5):
        """用户交互后的依恋更新。"""
        if character_id not in self._states:
            self.set_style(character_id, "secure")

        profile = self.get_profile(character_id)
        s = self._states[character_id]

        if positive:
            s["attachment_level"] = min(100, s["attachment_level"] +
                                        intensity * profile["intimacy_growth"] * 2)
            s["trust_level"] = min(100, s["trust_level"] +
                                   intensity * profile["trust_growth"] * 2)
            s["jealousy_level"] = max(0, s["jealousy_level"] - intensity * 3)
        else:
            s["trust_level"] = max(0, s["trust_level"] - intensity * 3)
            s["jealousy_level"] = min(100, s["jealousy_level"] + intensity * 5)

        s["last_interaction"] = datetime.now()
        self._persist(character_id)

    def on_tick(self, character_id: str) -> dict:
        """每 tick 自然衰减/增长。"""
        if character_id not in self._states:
            return {}

        profile = self.get_profile(character_id)
        s = self._states[character_id]

        # 依恋衰减
        decay = 0.1 * profile["decay_resistance"]
        s["attachment_level"] = max(5, s["attachment_level"] - decay)

        # 嫉妒衰减
        s["jealousy_level"] = max(0, s["jealousy_level"] - 0.05)

        # 长期不互动加速衰减
        hours_since = (datetime.now() - s["last_interaction"]).total_seconds() / 3600
        if hours_since > 24:
            s["attachment_level"] = max(5, s["attachment_level"] - hours_since * 0.02)
            s["trust_level"] = max(5, s["trust_level"] - hours_since * 0.01)

        self._persist(character_id)
        return dict(s)

    # ── 行为影响 ──

    def should_initiate_contact(self, character_id: str) -> bool:
        """判断是否应该主动联系用户。"""
        if character_id not in self._states:
            return False

        profile = self.get_profile(character_id)
        s = self._states[character_id]
        hours_since = (datetime.now() - s["last_interaction"]).total_seconds() / 3600

        # 冷却检查
        if character_id in self._contact_cooldown:
            if datetime.now() < self._contact_cooldown[character_id]:
                return False

        # 基础概率
        base_prob = profile["contact_frequency"] * 0.1
        # 依恋越高越主动
        attachment_factor = s["attachment_level"] / 100.0
        # 越久不联系越想联系（但 avoidant 风格反效果）
        time_factor = min(1.0, hours_since / 48) if character_id not in self._styles or self._styles[character_id] != "avoidant" else 0.2
        # 嫉妒越高越可能联系
        jealousy_factor = s["jealousy_level"] / 100.0

        prob = (base_prob + attachment_factor * 0.3 + time_factor * 0.3 + jealousy_factor * 0.1)

        if random.random() < prob:
            cooldown_hours = 4 / profile["contact_frequency"]  # secure~2h, anxious~1h, avoidant~10h
            self._contact_cooldown[character_id] = datetime.now() + timedelta(hours=max(1, cooldown_hours))
            return True
        return False

    def get_jealousy_threshold(self, character_id: str) -> float:
        """获取吃醋阈值。"""
        profile = self.get_profile(character_id)
        return profile["jealousy_threshold"]

    def get_avoidance_tendency(self, character_id: str) -> float:
        """获取回避倾向。"""
        profile = self.get_profile(character_id)
        return profile["avoidance_tendency"]

    # ── 查询 ──

    def get_state(self, character_id: str) -> dict:
        """获取当前依恋状态。"""
        if character_id not in self._states:
            return {}
        s = self._states[character_id]
        return {
            "style": self.get_style(character_id),
            "attachment_level": round(s.get("attachment_level", 0), 1),
            "trust_level": round(s.get("trust_level", 0), 1),
            "jealousy_level": round(s.get("jealousy_level", 0), 1),
            "last_interaction": str(s.get("last_interaction", "")),
        }

    def _persist(self, character_id: str):
        """持久化状态。"""
        if self.db:
            try:
                s = self._states[character_id]
                self.db.upsert_attachment_state(
                    character_id, self.get_style(character_id),
                    {
                        "attachment_level": s["attachment_level"],
                        "trust_level": s["trust_level"],
                        "jealousy_level": s["jealousy_level"],
                        "last_interaction": s["last_interaction"].isoformat(),
                    },
                )
            except Exception:
                pass
