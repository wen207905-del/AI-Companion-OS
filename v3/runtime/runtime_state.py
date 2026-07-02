"""
Runtime State — 运行时全局状态管理

记录 tick_count、life_loop 状态、错误计数等全局状态。
"""

import time
from threading import Lock


class RuntimeState:
    """运行时全局状态 — 线程安全的单例式状态管理器。"""

    def __init__(self):
        self._lock = Lock()
        self._state = {
            "tick_count": 0,
            "minute_tick_count": 0,
            "medium_tick_count": 0,
            "daily_tick_count": 0,
            "life_loop_status": "not_started",  # not_started / running / error / stopped
            "scheduler_status": "not_started",
            "last_tick_time": None,
            "last_error": None,
            "last_error_time": None,
            "error_count": 0,
            "total_decisions": 0,
            "total_actions": 0,
            "start_time": None,
            "uptime_seconds": 0,
        }

    def set(self, key: str, value):
        with self._lock:
            self._state[key] = value

    def get(self, key: str, default=None):
        with self._lock:
            return self._state.get(key, default)

    def increment(self, key: str, delta: int = 1):
        with self._lock:
            self._state[key] = self._state.get(key, 0) + delta

    def record_tick(self, level: str = "medium"):
        """记录一次 tick。"""
        with self._lock:
            self._state["tick_count"] += 1
            if level == "minute":
                self._state["minute_tick_count"] += 1
            elif level == "medium":
                self._state["medium_tick_count"] += 1
            elif level == "daily":
                self._state["daily_tick_count"] += 1
            self._state["last_tick_time"] = time.time()
            if self._state["start_time"]:
                self._state["uptime_seconds"] = int(time.time() - self._state["start_time"])

    def record_error(self, error: str):
        """记录一次错误。"""
        with self._lock:
            self._state["error_count"] += 1
            self._state["last_error"] = error
            self._state["last_error_time"] = time.time()

    def record_decision(self):
        with self._lock:
            self._state["total_decisions"] += 1

    def record_action(self):
        with self._lock:
            self._state["total_actions"] += 1

    def set_started(self):
        """标记系统已启动。"""
        with self._lock:
            self._state["start_time"] = time.time()
            self._state["life_loop_status"] = "running"
            self._state["scheduler_status"] = "running"

    def set_stopped(self):
        """标记系统已停止。"""
        with self._lock:
            self._state["life_loop_status"] = "stopped"
            self._state["scheduler_status"] = "stopped"
            if self._state["start_time"]:
                self._state["uptime_seconds"] = int(time.time() - self._state["start_time"])

    def set_errored(self, error: str):
        """标记系统错误。"""
        with self._lock:
            self._state["life_loop_status"] = "error"
            self._state["last_error"] = error
            self._state["last_error_time"] = time.time()

    def snapshot(self) -> dict:
        """获取当前状态快照。"""
        with self._lock:
            if self._state["start_time"] and self._state["life_loop_status"] == "running":
                self._state["uptime_seconds"] = int(time.time() - self._state["start_time"])
            return dict(self._state)
