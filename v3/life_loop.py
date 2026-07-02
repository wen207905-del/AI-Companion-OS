"""
统一生命循环入口 — WorldTickLifeLoop

每轮执行完整闭环：
  World Tick → Perception → Character State → Memory Retrieve →
  Emotion Update → Autonomy Decision → Central Brain →
  Action Dispatch → Feedback → Memory Writeback → 影响下一轮

集成：MoodPressure / AbsenceSystem / AutonomyEngine /
      CentralBrain / ActionDispatcher / FeedbackLoop
"""

import time
import threading
from datetime import datetime
from typing import Optional

from .db import V3Database
from .world.world_engine import WorldEngine
from .config import TICK_INTERVAL_SECONDS


class WorldTickLifeLoop:
    """V3 统一生命循环入口。

    负责每轮 tick 的完整闭环调度，将所有 Phase 2 子系统
    串联为一条可运行的生命管线。

    Usage::

        loop = WorldTickLifeLoop(db=db, enable_phase2=True)
        loop.run_once()            # 单次
        loop.run_loop(interval=300)  # 持续运行
    """

    def __init__(self, db: V3Database = None, tick_interval: int = None,
                 enable_phase2: bool = True):
        self.db = db or V3Database()
        self.tick_interval = tick_interval or TICK_INTERVAL_SECONDS
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tick_count = 0

        # ── 核心子系统 ──
        self.world_engine = WorldEngine()

        self._phase2 = enable_phase2
        self._mood_pressure = None
        self._absence_system = None
        self._autonomy_engine = None
        self._central_brain = None
        self._action_dispatcher = None
        self._feedback_loop = None

        if self._phase2:
            self._init_phase2()

    def _init_phase2(self):
        """初始化所有 Phase 2 子系统并完成依赖注入。"""
        try:
            from .world.mood_pressure import MoodPressureSystem
            from .world.absence_system import AbsenceSystem
            from .autonomy.autonomy_engine import AutonomyEngine
            from .autonomy.action_dispatcher import ActionDispatcher
            from .autonomy.feedback_loop import FeedbackLoop
            from .brain.central_brain import CentralBrain

            self._mood_pressure = MoodPressureSystem(self.db)
            self._absence_system = AbsenceSystem()
            self._autonomy_engine = AutonomyEngine()
            self._central_brain = CentralBrain()
            self._action_dispatcher = ActionDispatcher()
            self._feedback_loop = FeedbackLoop(self.db)

            # 注入依赖到子模块
            self._autonomy_engine.mood_pressure = self._mood_pressure
            self._autonomy_engine.absence_system = self._absence_system
            self._autonomy_engine.feedback_loop = self._feedback_loop
            self._action_dispatcher.feedback_loop = self._feedback_loop

            print("[LifeLoop] Phase 2 子系统初始化完成")
        except ImportError as e:
            print(f"[LifeLoop] Phase 2 子系统加载失败: {e}")
            self._phase2 = False

    # ═════════════════════════════════════════════════════════
    # 核心管线
    # ═════════════════════════════════════════════════════════

    def run_once(self) -> dict:
        """执行一次完整的生命循环。

        Pipeline:
          1. 感知世界（World Engine tick）
          2. 读取角色状态
          3. 读取近期记忆
          4. 更新情绪压力
          5. 计算自主行为（候选行为评分）
          6. 中央大脑仲裁
          7. 执行行为
          8. 写入记忆（Feedback Loop）
          9. 影响下一轮

        Returns:
            {tick_id, world_state, phase2_results, stats}
        """
        tick_id = self.db.get_tick_id()

        # ── Step 1: 感知世界 ──
        world_state = self.world_engine.tick()
        self.db.insert_world_state(tick_id, world_state.to_dict())
        for event in world_state.global_events:
            self.db.insert_world_event(
                tick_id=tick_id,
                event_type=event.get("type", "unknown"),
                event_desc=event.get("desc", ""),
            )

        # ── Step 2: 读取角色状态 ──
        characters = self.db.get_all_characters()

        # ── Step 3: 读取近期记忆（从 feedback_events） ──
        recent_memories = {}
        if self._phase2:
            for char in characters:
                char_id = char["character_id"]
                memories = self.db.get_recent_feedback_events(char_id, limit=5)
                recent_memories[char_id] = memories or []

        # ── Step 4: 更新情绪压力 ──
        if self._phase2 and self._mood_pressure:
            absence_modifier = (self._absence_system.get_user_inactive_factor()
                                if self._absence_system else 0.0)
            for char in characters:
                self._mood_pressure.update(
                    char["character_id"], tick_id,
                    absence_modifier=absence_modifier)

        # ── Step 5: 自主行为评分 ──
        decisions = {}
        if self._phase2 and self._autonomy_engine:
            for char in characters:
                char_id = char["character_id"]
                decision = self._autonomy_engine.evaluate(
                    character_id=char_id,
                    world_state=world_state,
                    emotion_state=self._get_emotion_state(char_id),
                    relationship_state=self._get_relationship_state(char_id),
                    personality={},
                    user_activity=self._get_user_activity(),
                    memory_context=self._build_memory_context(
                        recent_memories.get(char_id, [])),
                )
                decisions[char_id] = decision
                self.db.insert_autonomy_decision(
                    tick_id=tick_id,
                    character_id=char_id,
                    action_type=decision.get("action_type", "SILENCE"),
                    probability=decision.get("confidence", 0.0),
                    decision=str(decision),
                    reason=decision.get("reason", ""),
                )

        # ── Step 6-7: 执行行为 + 写入记忆 ──
        phase2_results = []
        if self._phase2:
            for char in characters:
                char_id = char["character_id"]
                decision = decisions.get(char_id, {})
                if not decision or not decision.get("should_act"):
                    continue

                # 中央大脑仲裁（如有）
                if self._central_brain:
                    decision = self._central_brain.arbitrate(
                        char_id, decision, world_state)

                # 执行行为
                result = self._action_dispatcher.dispatch(
                    char_id, decision["action_type"],
                    {"decision": decision, "world_state": world_state})

                phase2_results.append({
                    "character_id": char_id,
                    "decision": decision,
                    "execution": result,
                })

        # ── Step 9: 记录缺席日志 ──
        if self._phase2 and self._absence_system:
            absence_stage = self._absence_system.get_absence_stage()
            self.db.insert_absence_log(
                tick_id=tick_id,
                inactive_minutes=self._absence_system.get_inactive_minutes(),
                absence_stage=absence_stage.get("stage_name", "early"),
                effect_summary=str(absence_stage),
            )

        self._tick_count += 1

        return {
            "tick_id": tick_id,
            "world_state": world_state,
            "phase2_results": phase2_results,
            "stats": {
                "characters_count": len(characters),
                "decisions_made": len(decisions),
                "actions_executed": len(phase2_results),
            },
        }

    # ═════════════════════════════════════════════════════════
    # 状态辅助方法
    # ═════════════════════════════════════════════════════════

    def _get_emotion_state(self, character_id: str) -> dict:
        """获取角色当前情绪状态。"""
        if self._mood_pressure:
            return self._mood_pressure.get_pressure_for_autonomy(character_id)
        return {}

    def _get_relationship_state(self, character_id: str) -> dict:
        """获取角色关系状态。"""
        return {}  # Phase 2 暂为空，Phase 3 接 V2 关系引擎

    def _get_user_activity(self) -> dict:
        """获取用户活动状态。"""
        if self._absence_system:
            return {"inactive_minutes": self._absence_system.get_inactive_minutes()}
        return {"inactive_minutes": 0}

    def _build_memory_context(self, recent_memories: list) -> dict:
        """从近期反馈事件构建记忆上下文。"""
        return {
            "trigger_count": len(recent_memories),
            "recent_topics": [
                m.get("memory_entry", "") for m in recent_memories
                if m.get("memory_entry")
            ],
        }

    # ═════════════════════════════════════════════════════════
    # 运行控制
    # ═════════════════════════════════════════════════════════

    def run_loop(self, interval: int = None):
        """持续运行生命循环（后台线程）。

        Args:
            interval: tick 间隔秒数，默认使用构造参数
        """
        if interval is None:
            interval = self.tick_interval
        self._running = True
        self._thread = threading.Thread(
            target=self._loop_target, args=(interval,), daemon=True)
        self._thread.start()
        print(f"[LifeLoop] 生命循环已启动，间隔 {interval}s")

    def _loop_target(self, interval: int):
        """后台线程主循环。"""
        while self._running:
            try:
                self.run_once()
            except Exception:
                import traceback
                traceback.print_exc()
            for _ in range(interval):
                if not self._running:
                    break
                time.sleep(1)

    def stop(self):
        """停止生命循环。"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        self.db.close()
        print("[LifeLoop] 生命循环已停止")

    def get_status(self) -> dict:
        """获取运行状态。"""
        return {
            "running": self._running,
            "tick_count": self._tick_count,
            "tick_interval": self.tick_interval,
            "phase2_enabled": self._phase2,
            "current_time": datetime.now().isoformat(),
        }
