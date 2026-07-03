"""
V4 World Event System — 世界事件系统

事件类型：natural / social / user_action / time_based。
支持事件链：一个事件触发连锁反应。
"""

import json
import random
from datetime import datetime
from typing import Optional

# ── 事件类型 ──
EVENT_TYPES = ["natural", "social", "user_action", "time_based"]

# ── 默认事件模板 ──
EVENT_TEMPLATES = {
    "natural": [
        {"name": "sunrise", "emotion_bias": {"happy": 5, "sleepy": -10}, "intensity": 0.3},
        {"name": "rain_start", "emotion_bias": {"sad": 5, "calm": 10, "excited": -5}, "intensity": 0.5},
        {"name": "rain_stop", "emotion_bias": {"happy": 5, "calm": -5}, "intensity": 0.3},
        {"name": "thunderstorm", "emotion_bias": {"angry": 5, "lonely": 10}, "intensity": 0.7},
        {"name": "sunset", "emotion_bias": {"calm": 10, "lonely": 5}, "intensity": 0.4},
        {"name": "windy", "emotion_bias": {"excited": 5, "sleepy": -5}, "intensity": 0.3},
    ],
    "social": [
        {"name": "character_online", "emotion_bias": {"happy": 3}, "intensity": 0.2},
        {"name": "character_offline", "emotion_bias": {"lonely": 5}, "intensity": 0.3},
        {"name": "group_chat", "emotion_bias": {"excited": 10, "happy": 5}, "intensity": 0.6},
    ],
    "user_action": [
        {"name": "user_login", "emotion_bias": {"happy": 8, "miss_user": -15}, "intensity": 0.5},
        {"name": "user_send_message", "emotion_bias": {"happy": 10, "excited": 8}, "intensity": 0.6},
        {"name": "user_silent_24h", "emotion_bias": {"lonely": 15, "miss_user": 20, "sad": 8}, "intensity": 0.7},
        {"name": "user_silent_72h", "emotion_bias": {"lonely": 25, "miss_user": 30, "sad": 15, "angry": 5}, "intensity": 0.85},
    ],
    "time_based": [
        {"name": "morning", "emotion_bias": {"sleepy": -20, "excited": 5}, "intensity": 0.4},
        {"name": "noon", "emotion_bias": {"sleepy": 5, "calm": 5}, "intensity": 0.2},
        {"name": "evening", "emotion_bias": {"calm": 10, "lonely": 5}, "intensity": 0.3},
        {"name": "night", "emotion_bias": {"sleepy": 20, "lonely": 10}, "intensity": 0.5},
        {"name": "holiday", "emotion_bias": {"happy": 15, "excited": 12}, "intensity": 0.7},
        {"name": "weekend", "emotion_bias": {"happy": 8, "excited": 5}, "intensity": 0.4},
    ],
}


class WorldEvent:
    """单个世界事件。"""

    def __init__(self, name: str, event_type: str, intensity: float = 0.5,
                 emotion_bias: dict = None, target_chars: list = None,
                 chain_triggers: list = None, duration_ticks: int = 1):
        self.name = name
        self.event_type = event_type
        self.intensity = intensity
        self.emotion_bias = emotion_bias or {}
        self.target_chars = target_chars or []  # 空=所有角色
        self.chain_triggers = chain_triggers or []  # [event_name, ...]
        self.duration_ticks = duration_ticks
        self.remaining_ticks = duration_ticks
        self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "name": self.name, "type": self.event_type,
            "intensity": self.intensity, "emotion_bias": self.emotion_bias,
            "remaining_ticks": self.remaining_ticks,
        }


class EventSystem:
    """世界事件系统。

    管理事件的创建、持续、连锁触发。
    """

    def __init__(self, db=None, event_bus=None):
        self.db = db
        self.event_bus = event_bus
        self._active_events: list = []  # [WorldEvent, ...]
        self._event_queue: list = []    # 待处理事件

    # ── 事件创建 ──

    def create_event(self, name: str, event_type: str,
                     intensity: float = 0.5, emotion_bias: dict = None,
                     target_chars: list = None, chain_triggers: list = None,
                     duration_ticks: int = 1) -> WorldEvent:
        """创建一个世界事件。"""
        event = WorldEvent(
            name=name, event_type=event_type,
            intensity=intensity, emotion_bias=emotion_bias,
            target_chars=target_chars, chain_triggers=chain_triggers,
            duration_ticks=duration_ticks,
        )

        if duration_ticks > 0:
            self._active_events.append(event)

        self._notify(event, "created")

        if self.db:
            try:
                self.db.insert_world_event(event.to_dict())
            except Exception:
                pass

        return event

    def create_from_template(self, event_type: str, template_name: str,
                              custom_bias: dict = None) -> Optional[WorldEvent]:
        """从模板创建事件。"""
        templates = EVENT_TEMPLATES.get(event_type, [])
        for tmpl in templates:
            if tmpl["name"] == template_name:
                bias = dict(tmpl["emotion_bias"])
                if custom_bias:
                    bias.update(custom_bias)
                return self.create_event(
                    name=template_name,
                    event_type=event_type,
                    intensity=tmpl["intensity"],
                    emotion_bias=bias,
                    duration_ticks=2 if event_type == "natural" else 1,
                )
        return None

    # ── Tick 处理 ──

    def tick(self) -> dict:
        """处理一个 tick：减少事件持续时间、触发事件链、清理过期事件。"""
        expired = []
        chain_events = []

        for event in self._active_events:
            event.remaining_ticks -= 1
            if event.remaining_ticks <= 0:
                # 事件过期，触发链式事件
                expired.append(event)
                for chain_name in event.chain_triggers:
                    chain = self._create_chain_event(chain_name, event)
                    if chain:
                        chain_events.append(chain.name)

        for event in expired:
            self._active_events.remove(event)
            self._notify(event, "expired")

        return {
            "active_count": len(self._active_events),
            "expired_count": len(expired),
            "chain_triggered": chain_events,
        }

    def _create_chain_event(self, name: str, source_event: WorldEvent):
        """从事件链创建衍生事件。"""
        for cat, templates in EVENT_TEMPLATES.items():
            for tmpl in templates:
                if tmpl["name"] == name:
                    return self.create_event(
                        name=name,
                        event_type=cat,
                        intensity=tmpl["intensity"] * source_event.intensity,
                        emotion_bias=tmpl["emotion_bias"],
                        duration_ticks=1,
                    )
        return None

    # ── 查询 ──

    def get_active_events(self) -> list:
        """获取当前活跃的事件列表。"""
        return [e.to_dict() for e in self._active_events]

    def get_emotion_bias_for_character(self, character_id: str) -> dict:
        """计算当前所有事件对指定角色的情绪偏差总和。"""
        total_bias = {}
        for event in self._active_events:
            if not event.target_chars or character_id in event.target_chars:
                for dim, bias in event.emotion_bias.items():
                    total_bias[dim] = total_bias.get(dim, 0) + bias * event.intensity
        return total_bias

    # ── 内部 ──

    def _notify(self, event: WorldEvent, action: str):
        """通过事件总线通知。"""
        if self.event_bus:
            self.event_bus.publish("world_event", {
                "action": action,
                "event": event.to_dict(),
                "timestamp": datetime.now().isoformat(),
            })
