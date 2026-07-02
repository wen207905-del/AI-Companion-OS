"""
事件总线（Event Bus）：接收原始输入，创建事件，分发到各引擎。
"""
import json
import uuid
from typing import Optional
from dataclasses import dataclass, field, asdict

from engine.world_clock import now as world_now


@dataclass
class Event:
    event_id: str
    event_type: str          # conversation, accompany, gift, anniversary, time_passive, system
    timestamp: float
    participants: list       # ["user", "ye_ruxue", ...]
    raw_input: Optional[str] = None
    weight: int = 1
    metadata: dict = field(default_factory=dict)


class EventBus:
    """事件总线：单例，管理事件的分发和处理"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._handlers = {}      # event_type → [handler_fn]
        self._event_log = []     # 内存缓存最近事件
        self._initialized = True

    def subscribe(self, event_type: str, handler):
        """注册事件处理器"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def create_event(self, event_type: str, participants: list,
                     raw_input: str = None, weight: int = 1,
                     metadata: dict = None, timestamp: float | None = None) -> Event:
        """创建事件"""
        event = Event(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            event_type=event_type,
            timestamp=world_now() if timestamp is None else timestamp,
            participants=participants,
            raw_input=raw_input,
            weight=weight,
            metadata=metadata or {}
        )
        self._event_log.append(event)
        return event

    def dispatch(self, event: Event):
        """分发事件到所有匹配的处理器"""
        results = []
        handlers = self._handlers.get(event.event_type, [])
        wildcard_handlers = self._handlers.get("*", [])
        all_handlers = handlers + wildcard_handlers

        for handler in all_handlers:
            result = handler(event)
            if result is not None:
                results.append(result)
        return results

    def get_recent_events(self, character_id: str, limit: int = 20):
        """获取某角色相关的最近事件"""
        recent = []
        for event in reversed(self._event_log):
            if character_id in event.participants:
                recent.append(event)
                if len(recent) >= limit:
                    break
        return recent


# 全局单例
event_bus = EventBus()
