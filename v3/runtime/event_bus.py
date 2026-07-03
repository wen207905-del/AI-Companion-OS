"""
Event Bus — 事件总线

所有引擎通过事件总线通信，支持 publish/subscribe 模式。

事件类型：
  - world_tick         世界 Tick
  - tick_minute        1分钟级 Tick
  - tick_medium        5分钟级 Tick
  - tick_daily         每天0点 Tick
  - emotion_change     情绪变化
  - autonomy_decision  自主决策
  - action_executed    行为执行完成
  - user_message       用户消息
  - user_absence       用户缺席检测
  - memory_written     记忆写入
  - calendar_event     日历事件触发
  - world_event        世界事件触发
"""

import threading
from collections import defaultdict
from typing import Callable, Any


class EventBus:
    """事件总线 — V4 各子系统通信中枢。

    支持 publish/subscribe，线程安全。
    """

    _instance = None
    _class_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "EventBus":
        if cls._instance is None:
            with cls._class_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    VALID_EVENT_TYPES = {
        "world_tick", "tick_minute", "tick_medium", "tick_daily",
        "emotion_change", "autonomy_decision", "action_executed",
        "user_message", "user_absence", "memory_written",
        "calendar_event", "world_event",
    }

    def __init__(self):
        self._subscribers: dict = defaultdict(list)
        self._lock = threading.Lock()
        self._event_history: list = []  # 最近 100 条事件

    def subscribe(self, event_type: str, callback: Callable):
        """订阅事件。

        Args:
            event_type: 事件类型（支持 '*' 订阅全部）
            callback: 回调函数 callback(event_type, data)
        """
        with self._lock:
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        """取消订阅。"""
        with self._lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)

    def publish(self, event_type: str, data: dict = None):
        """发布事件。

        Args:
            event_type: 事件类型
            data: 事件数据
        """
        data = data or {}
        event = {"type": event_type, "data": data}

        # 记录历史（最多 100 条）
        self._event_history.append(event)
        if len(self._event_history) > 100:
            self._event_history = self._event_history[-100:]

        # 通知订阅者
        with self._lock:
            callbacks = (
                self._subscribers.get(event_type, [])
                + self._subscribers.get("*", [])
            )

        for cb in callbacks:
            try:
                cb(event_type, data)
            except Exception:
                pass  # 订阅者异常不应中断事件分发

    def get_history(self, limit: int = 20) -> list:
        """获取最近的事件历史。"""
        return self._event_history[-limit:]

    def get_subscriber_count(self, event_type: str = None) -> int:
        """获取指定事件类型（或全部）的订阅者数量。"""
        with self._lock:
            if event_type:
                return len(self._subscribers.get(event_type, []))
            return sum(len(v) for v in self._subscribers.values())

    def clear_history(self):
        """清空事件历史（调试用）。"""
        self._event_history.clear()
