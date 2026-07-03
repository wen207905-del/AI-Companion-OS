"""
V4 Identity State — 人格状态追踪

每个角色的依恋度、信任度、亲密度及其变化日志。
"""

from datetime import datetime
from typing import Optional


class IdentityState:
    """人格状态管理器。

    追踪三个核心维度：
    - attachment_level：依恋度 (0-100)
    - trust_level：信任度 (0-100)
    - intimacy_level：亲密度 (0-100)
    """

    def __init__(self, db=None, event_bus=None):
        self.db = db
        self.event_bus = event_bus
        self._states: dict = {}  # char_id → {attachment, trust, intimacy, history: []}

    def get_state(self, character_id: str) -> dict:
        """获取角色人格状态。"""
        if character_id not in self._states:
            self._states[character_id] = {
                "attachment": 30,
                "trust": 40,
                "intimacy": 10,
                "history": [],
            }
        s = self._states[character_id]
        return {
            "attachment_level": s["attachment"],
            "trust_level": s["trust"],
            "intimacy_level": s["intimacy"],
            "history_count": len(s.get("history", [])),
        }

    def update(self, character_id: str,
               attachment_delta: float = 0,
               trust_delta: float = 0,
               intimacy_delta: float = 0,
               trigger: str = "system") -> dict:
        """更新人格状态并记录日志。"""
        if character_id not in self._states:
            self.get_state(character_id)  # 初始化

        s = self._states[character_id]
        old = {"attachment": s["attachment"], "trust": s["trust"], "intimacy": s["intimacy"]}

        s["attachment"] = max(0, min(100, s["attachment"] + attachment_delta))
        s["trust"] = max(0, min(100, s["trust"] + trust_delta))
        s["intimacy"] = max(0, min(100, s["intimacy"] + intimacy_delta))

        change = {
            "timestamp": datetime.now().isoformat(),
            "trigger": trigger,
            "attachment_delta": round(attachment_delta, 1),
            "trust_delta": round(trust_delta, 1),
            "intimacy_delta": round(intimacy_delta, 1),
            "before": old,
            "after": {
                "attachment": s["attachment"],
                "trust": s["trust"],
                "intimacy": s["intimacy"],
            },
        }
        s.setdefault("history", []).append(change)
        if len(s["history"]) > 100:
            s["history"] = s["history"][-100:]

        # 发布事件
        if self.event_bus:
            self.event_bus.publish("identity_change", {
                "character_id": character_id, **change,
            })

        # 持久化
        if self.db:
            try:
                self.db.insert_relationship_snapshot(
                    character_id=character_id,
                    tick_id=0,
                    attachment=s["attachment"],
                    trust=s["trust"],
                    intimacy=s["intimacy"],
                )
            except Exception:
                pass

        return change

    def get_attachment_style(self, character_id: str) -> str:
        """根据状态推断当前依恋风格。"""
        s = self.get_state(character_id)
        a = s["attachment_level"]
        t = s["trust_level"]

        if a >= 60 and t >= 60:
            return "secure"
        elif a >= 60 and t < 40:
            return "anxious"
        elif a < 30 and t >= 50:
            return "avoidant"
        elif a < 30 and t < 30:
            return "fearful"
        return "developing"
