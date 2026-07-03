"""
V4 Life Kernel — 统一运行内核

以 tick 驱动整个系统，是 V4 的最高优先级核心模块。
每 tick 执行完整生命循环：感知 → 记忆 → 情绪 → 关系 → 决策 → 分发 → 反馈。

状态机：IDLE → RUNNING → PAUSED → ERROR
"""

import time
import threading
from datetime import datetime
from enum import Enum
from typing import Optional


class KernelState(Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    STOPPING = "stopping"


class LifeKernel:
    """V4 数字生命内核。

    统一 tick 驱动管线：
        world → perception → memory → emotion → relationship → autonomy → action → feedback
    """

    def __init__(self, tick_interval: float = 60.0, db=None, event_bus=None):
        self.tick_interval = tick_interval  # 秒
        self.db = db
        self.event_bus = event_bus
        self.state = KernelState.IDLE
        self.tick_count: int = 0
        self.uptime_start: Optional[float] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # 子系统引用（延迟注入）
        self.emotion_engine = None
        self.memory_core = None
        self.identity_state = None
        self.autonomy_engine = None
        self.intention_engine = None
        self.attachment_model = None
        self.world_engine = None
        self.social_graph = None
        self.event_system = None
        self.action_dispatcher = None
        self.feedback_loop = None
        self.perception_manager = None

    # ── 状态管理 ──

    def start(self, background: bool = True):
        """启动生命内核。"""
        with self._lock:
            if self.state == KernelState.RUNNING:
                return
            self.state = KernelState.RUNNING
            self.uptime_start = time.time()
            self._stop_event.clear()
            self.tick_count = 0

        self._log_state_change()
        self._record_tick_event("kernel_started")

        if background:
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
        else:
            self.tick()  # 立即执行一次

    def stop(self):
        """停止生命内核。"""
        with self._lock:
            self.state = KernelState.STOPPING
        self._stop_event.set()
        self._log_state_change()
        self._record_tick_event("kernel_stopped")
        if self._thread:
            self._thread.join(timeout=5)
        with self._lock:
            self.state = KernelState.IDLE

    def pause(self):
        """暂停。"""
        with self._lock:
            if self.state == KernelState.RUNNING:
                self.state = KernelState.PAUSED
        self._log_state_change()

    def resume(self):
        """恢复。"""
        with self._lock:
            if self.state == KernelState.PAUSED:
                self.state = KernelState.RUNNING
        self._log_state_change()

    # ── 核心循环 ──

    def _run_loop(self):
        """后台持续运行循环。"""
        while not self._stop_event.is_set():
            if self.state == KernelState.RUNNING:
                try:
                    self.tick()
                except Exception as e:
                    self._handle_error(e)
            self._stop_event.wait(timeout=self.tick_interval)

    def tick(self) -> dict:
        """执行一次完整生命循环。

        Returns:
            {'tick_id': str, 'duration_ms': float, 'steps': {...}, 'errors': [...]}
        """
        t_start = time.time()
        tick_id = f"tick_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{self.tick_count}"
        result = {"tick_id": tick_id, "duration_ms": 0, "steps": {}, "errors": []}

        # Pipeline steps — 每步异常隔离
        pipeline = [
            ("perception", self._step_perception),
            ("memory_retrieve", self._step_memory_retrieve),
            ("emotion_update", self._step_emotion_update),
            ("relationship_update", self._step_relationship_update),
            ("autonomy_decision", self._step_autonomy_decision),
            ("action_dispatch", self._step_action_dispatch),
            ("feedback_writeback", self._step_feedback_writeback),
        ]

        for step_name, step_fn in pipeline:
            try:
                step_result = step_fn()
                result["steps"][step_name] = step_result
            except Exception as e:
                result["errors"].append({"step": step_name, "error": str(e)})
                # 继续执行后续步骤（异常隔离）

        with self._lock:
            self.tick_count += 1

        result["duration_ms"] = round((time.time() - t_start) * 1000, 2)
        self._record_tick_to_db(tick_id, result)
        return result

    # ── Pipeline Steps ──

    def _step_perception(self) -> dict:
        """Step 1: 世界感知。"""
        if self.perception_manager:
            return self.perception_manager.perceive()
        if self.world_engine:
            ws = self.world_engine.get_state()
            return {"world": str(ws)[:200] if ws else "no_state"}
        return {"world": "not_configured"}

    def _step_memory_retrieve(self) -> dict:
        """Step 2: 记忆检索。"""
        if self.memory_core:
            return self.memory_core.retrieve_context(context="current_tick")
        return {"memories": []}

    def _step_emotion_update(self) -> dict:
        """Step 3: 情绪更新。"""
        if self.emotion_engine:
            return self.emotion_engine.update_all()
        return {"emotions": "not_configured"}

    def _step_relationship_update(self) -> dict:
        """Step 4: 关系更新。"""
        if self.social_graph:
            return self.social_graph.tick_update()
        return {"relationships": "not_configured"}

    def _step_autonomy_decision(self) -> dict:
        """Step 5: 自主决策。"""
        if self.autonomy_engine:
            return self.autonomy_engine.decide_all()
        return {"decisions": []}

    def _step_action_dispatch(self) -> dict:
        """Step 6: 行为分发。"""
        if self.action_dispatcher:
            return self.action_dispatcher.dispatch_pending()
        return {"dispatched": 0}

    def _step_feedback_writeback(self) -> dict:
        """Step 7: 反馈写回。"""
        if self.feedback_loop:
            return self.feedback_loop.flush()
        return {"written": 0}

    # ── 数据库 & 错误处理 ──

    def _record_tick_to_db(self, tick_id: str, result: dict):
        """记录 tick 到 life_loop_ticks 表。"""
        if self.db:
            try:
                pg = getattr(self.db, '_db_type', 'sqlite') == 'postgres'
                ph = "%s" if pg else "?"
                sql = f"""
                    INSERT INTO life_loop_ticks (tick_id, state, tick_count, duration_ms, error_count)
                    VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
                """
                self.db._execute(sql, (tick_id, self.state.value, self.tick_count,
                                        result["duration_ms"], len(result["errors"])))
                self.db.commit()
            except Exception:
                pass

    def _record_tick_event(self, event_type: str):
        """记录内核事件。"""
        if self.event_bus:
            try:
                self.event_bus.publish("kernel_event", {
                    "type": event_type, "state": self.state.value,
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception:
                pass

    def _handle_error(self, error: Exception):
        """异常处理 — 降级为 ERROR 但不崩溃。"""
        with self._lock:
            self.state = KernelState.ERROR
        self._log_state_change()
        print(f"[LifeKernel] ERROR: {error}")

    def _log_state_change(self):
        """记录状态变更。"""
        print(f"[LifeKernel] 状态变更 → {self.state.value}")

    # ── 查询接口 ──

    def get_status(self) -> dict:
        """返回内核运行状态。"""
        uptime = 0
        if self.uptime_start:
            uptime = time.time() - self.uptime_start
        return {
            "state": self.state.value,
            "tick_count": self.tick_count,
            "uptime_seconds": round(uptime, 1),
            "tick_interval": self.tick_interval,
        }


# ── 便捷工厂 ──

def create_life_kernel(db=None, event_bus=None,
                        tick_interval: float = 60.0) -> LifeKernel:
    """创建并初始化 LifeKernel 实例。"""
    kernel = LifeKernel(tick_interval=tick_interval, db=db, event_bus=event_bus)
    return kernel
