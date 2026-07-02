"""
Runtime Scheduler — 多频调度器

三层调度：
  - 1分钟级（高频）：角色内部状态更新、情绪衰减、缺席检查
  - 5分钟级（中频）：World Tick、天气影响、活动变化
  - 每天0点（低频）：日记结算、记忆巩固、关系趋势计算

与 Life Loop / Event Bus 配合，驱动整个 V4 生命循环。
"""

import time
import threading
from datetime import datetime, time as dt_time
from typing import Callable, Optional
from enum import Enum


class TickLevel(Enum):
    MINUTE = "minute"     # 1 分钟
    MEDIUM = "medium"     # 5 分钟
    DAILY = "daily"       # 每天 0 点


class Scheduler:
    """多频调度器 — V4 Runtime Kernel 核心。

    驱动三层定时任务，通过 EventBus 发布 tick 事件。
    """

    MINUTE_INTERVAL = 60       # 1 分钟
    MEDIUM_INTERVAL = 300      # 5 分钟
    DAILY_CHECK_INTERVAL = 60  # 每 60 秒检查一次是否到 0 点

    def __init__(self, event_bus=None, life_loop=None):
        self.event_bus = event_bus
        self.life_loop = life_loop
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tick_counts = {TickLevel.MINUTE: 0, TickLevel.MEDIUM: 0, TickLevel.DAILY: 0}
        self._last_daily = None
        self._last_minute = 0.0
        self._last_medium = 0.0

    # ── 启动 / 停止 ──

    def start(self, block: bool = False):
        """启动调度器。"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        if block:
            self._thread.join()

    def stop(self):
        """停止调度器。"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def is_running(self) -> bool:
        return self._running

    # ── 状态 ──

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "tick_counts": {k.value: v for k, v in self._tick_counts.items()},
            "last_daily": str(self._last_daily) if self._last_daily else None,
        }

    def get_minute_count(self) -> int:
        return self._tick_counts[TickLevel.MINUTE]

    def get_medium_count(self) -> int:
        return self._tick_counts[TickLevel.MEDIUM]

    def get_daily_count(self) -> int:
        return self._tick_counts[TickLevel.DAILY]

    # ── 内部循环 ──

    def _run_loop(self):
        """后台轮询线程。"""
        while self._running:
            now = time.time()

            # 1 分钟级
            if now - self._last_minute >= self.MINUTE_INTERVAL:
                self._last_minute = now
                self._tick_minute()

            # 5 分钟级
            if now - self._last_medium >= self.MEDIUM_INTERVAL:
                self._last_medium = now
                self._tick_medium()

            # 每天 0 点检测
            self._check_daily()

            time.sleep(1)

    def _tick_minute(self):
        """1 分钟级 tick：角色内部状态更新、情绪衰减、缺席检查。"""
        self._tick_counts[TickLevel.MINUTE] += 1
        if self.event_bus:
            self.event_bus.publish("tick_minute",
                {"tick_level": "minute", "tick_count": self._tick_counts[TickLevel.MINUTE]})
        if self.life_loop:
            try:
                self.life_loop.run_minute_tick()
            except Exception:
                pass

    def _tick_medium(self):
        """5 分钟级 tick：World Tick、天气影响、活动变化。"""
        self._tick_counts[TickLevel.MEDIUM] += 1
        if self.event_bus:
            self.event_bus.publish("tick_medium",
                {"tick_level": "medium", "tick_count": self._tick_counts[TickLevel.MEDIUM]})
        if self.life_loop:
            try:
                self.life_loop.run_once()
            except Exception:
                pass

    def _check_daily(self):
        """检查是否触发每天 0 点 tick（避免同一天重复）。"""
        now = datetime.now()
        today = now.date()
        if now.hour == 0 and now.minute == 0 and self._last_daily != today:
            self._last_daily = today
            self._tick_daily()

    def _tick_daily(self):
        """每天 0 点 tick：日记结算、记忆巩固、关系趋势计算。"""
        self._tick_counts[TickLevel.DAILY] += 1
        if self.event_bus:
            self.event_bus.publish("tick_daily",
                {"tick_level": "daily", "tick_count": self._tick_counts[TickLevel.DAILY]})
        if self.life_loop:
            try:
                self.life_loop.run_daily_tick()
            except Exception:
                pass

    # ── 手动触发 ──

    def trigger_manual(self, level: str):
        """手动触发指定层级 tick（调试用）。"""
        if level == "minute":
            self._tick_minute()
        elif level == "medium":
            self._tick_medium()
        elif level == "daily":
            self._tick_daily()
