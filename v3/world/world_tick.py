"""
世界主循环

V3 核心运行循环，每 5 分钟 tick 一次：
Phase 1: 驱动时间推进 / 天气更新 / 角色活动
Phase 2: 情绪压力累积 / 缺席追踪 / 自主决策 / 中央大脑仲裁 / 行为调度 / 反馈闭环
"""

import time
import threading
import json
from datetime import datetime

from .world_engine import WorldEngine
from ..db import V3Database
from ..config import TICK_INTERVAL_SECONDS


class WorldTick:
    """世界主循环管理器。

    以守护线程方式运行，每 N 秒执行一次 tick。
    支持 --phase2 模式，注入完整自主行为决策链路。
    """

    def __init__(self, db: V3Database = None, tick_interval: int = None,
                 enable_phase2: bool = False):
        """
        Args:
            db: V3 数据库实例，不传则自动创建
            tick_interval: tick 间隔（秒），默认从 config 读取
            enable_phase2: 是否启用 Phase 2 自主行为链路
        """
        self.db = db or V3Database()
        self.tick_interval = tick_interval or TICK_INTERVAL_SECONDS
        self.world_engine = WorldEngine()
        self._running = False
        self._thread: threading.Thread = None
        self._tick_count = 0
        self._on_tick_callbacks: list = []

        # Phase 2 子系统（惰性初始化）
        self._phase2 = enable_phase2
        self._mood_pressure = None
        self._absence_system = None
        self._autonomy_engine = None
        self._central_brain = None
        self._decision_factors = None
        self._feedback_loop = None

        if self._phase2:
            self._init_phase2()

    def _init_phase2(self):
        """惰性初始化所有 Phase 2 子系统。"""
        try:
            from ..world.mood_pressure import MoodPressureSystem
            from ..world.absence_system import AbsenceSystem
            from ..autonomy.decision_factors import DecisionFactors
            from ..autonomy.autonomy_engine import AutonomyEngine
            from ..autonomy.action_policy import ActionPolicy
            from ..autonomy.action_dispatcher import ActionDispatcher
            from ..autonomy.feedback_loop import FeedbackLoop
            from ..brain.scene_classifier import SceneClassifier
            from ..brain.state_arbiter import StateArbiter
            from ..brain.central_brain import CentralBrain

            self._mood_pressure = MoodPressureSystem(self.db)
            self._absence_system = AbsenceSystem()
            self._decision_factors = DecisionFactors()
            self._action_policy = ActionPolicy()
            self._action_dispatcher = ActionDispatcher()
            self._feedback_loop = FeedbackLoop(self.db)
            self._scene_classifier = SceneClassifier()
            self._state_arbiter = StateArbiter()
            self._central_brain = CentralBrain()
            self._autonomy_engine = AutonomyEngine()

            # 将 Phase 2 子系统注入到 Autonomy Engine
            engine = self._autonomy_engine
            engine.decision_factors = self._decision_factors
            engine.action_policy = self._action_policy
            engine.action_dispatcher = self._action_dispatcher
            engine.feedback_loop = self._feedback_loop
            engine.central_brain = self._central_brain
            print("[WorldTick] Phase 2 子系统初始化完成")
        except ImportError as e:
            print(f"[WorldTick] Phase 2 子系统加载失败，回退到 Phase 1: {e}")
            self._phase2 = False

    # ═════════════════════════════════════════════════════════
    # 生命周期
    # ═════════════════════════════════════════════════════════

    def start(self, block: bool = False):
        """启动世界循环。

        Args:
            block: 是否阻塞当前线程
        """
        if self._running:
            print("[WorldTick] 世界循环已在运行中")
            return

        self.db.connect()
        self.db.create_tables()

        self._running = True
        mode = "Phase 2" if self._phase2 else "Phase 1"
        print(f"[WorldTick] 世界循环已启动 ({mode})，tick 间隔: {self.tick_interval}s")

        if block:
            self._run_loop()
        else:
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def stop(self):
        """停止世界循环。"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        self.db.close()
        print("[WorldTick] 世界循环已停止")

    def register_callback(self, callback):
        """注册 tick 回调。"""
        self._on_tick_callbacks.append(callback)

    # ═════════════════════════════════════════════════════════
    # Tick 主逻辑
    # ═════════════════════════════════════════════════════════

    def tick_once(self) -> dict:
        """手动执行一次 tick（Phase 1 + 可选 Phase 2）。

        Returns:
            {tick_id, world_state, phase2_results?}
        """
        tick_id = self.db.get_tick_id()
        world_state = self.world_engine.tick()

        # ── Phase 1: 基础世界状态写入 ──
        self.db.insert_world_state(tick_id, world_state.to_dict())
        for event in world_state.global_events:
            self.db.insert_world_event(
                tick_id=tick_id,
                event_type=event.get("type", "unknown"),
                event_desc=event.get("desc", ""),
            )
        self._update_character_activities(tick_id, world_state)

        result = {"tick_id": tick_id, "world_state": world_state}

        # ── Phase 2: 自主行为完整链路 ──
        if self._phase2:
            phase2_results = self._run_phase2_pipeline(tick_id, world_state)
            result["phase2_results"] = phase2_results

        # 触发外部回调
        for cb in self._on_tick_callbacks:
            try:
                cb(tick_id, world_state)
            except Exception as e:
                print(f"[WorldTick] 回调异常: {e}")

        self._tick_count += 1
        return result

    def _run_phase2_pipeline(self, tick_id: int, world_state) -> list:
        """执行完整 Phase 2 自主行为链路。

        Pipeline:
          World State → Mood Pressure → Absence →
          Decision Factors → Autonomy Engine → Central Brain →
          Execute Actions → Feedback Loop

        Returns:
            每个角色的决策和执行结果列表
        """
        results = []
        characters = self.db.get_all_characters()
        if not characters:
            return results

        # Step 1: 情绪压力累积（一次性全局更新）
        for char in characters:
            char_id = char["character_id"]
            absence_modifier = self._absence_system.get_user_inactive_factor()
            self._mood_pressure.update(char_id, tick_id,
                                       absence_modifier=absence_modifier)

        # Step 2: 缺席系统快照
        absence_stage = self._absence_system.get_absence_stage()
        inactive_minutes = self._absence_system.get_inactive_minutes()
        self.db.insert_absence_log(
            tick_id=tick_id,
            inactive_minutes=inactive_minutes,
            absence_stage=absence_stage.get("stage_name", "early"),
            effect_summary=str(absence_stage),
        )

        # Step 3-6: 对每个角色执行自主决策回路
        for char in characters:
            char_id = char["character_id"]

            # 自主决策 → 中央脑仲裁 → 执行 → 反馈
            decision = self._autonomy_engine.evaluate(
                character_id=char_id,
                world_state=world_state,
                emotion_state={},
                relationship_state={},
                personality={},
                user_activity={},
                memory_context={},
            )

            # 持久化决策记录
            self.db.insert_autonomy_decision(
                tick_id=tick_id,
                character_id=char_id,
                action_type=decision.get("action_type", "SILENCE"),
                probability=decision.get("confidence", 0.0),
                decision=str(decision),
                reason=decision.get("reason", ""),
            )

            results.append({
                "character_id": char_id,
                "decision": decision,
            })

        return results

    # ═════════════════════════════════════════════════════════
    # 内部
    # ═════════════════════════════════════════════════════════

    def _run_loop(self):
        """内部运行循环。"""
        while self._running:
            try:
                result = self.tick_once()
                if self._tick_count == 1:
                    ws = result["world_state"]
                    print(
                        f"[WorldTick #{result['tick_id']}] "
                        f"{ws.time_period} | {ws.weather.label} "
                        f"{ws.weather.temperature}°C | {ws.environment.atmosphere}"
                    )
                    if self._phase2 and "phase2_results" in result:
                        for r in result["phase2_results"]:
                            d = r["decision"]
                            print(f"  {r['character_id']}: {d.get('action_type')} "
                                  f"(score={d.get('score', 0):.1f})")
            except Exception as e:
                print(f"[WorldTick] tick 异常: {e}")

            for _ in range(int(self.tick_interval)):
                if not self._running:
                    break
                time.sleep(1)

    def _update_character_activities(self, tick_id: int, world_state):
        """更新所有角色的当前活动。"""
        characters = self.db.get_all_characters()
        if not characters:
            return

        for char in characters:
            char_id = char["character_id"]
            activity = self.world_engine.get_recommended_activity(char_id)
            self.db.upsert_character_state(
                character_id=char_id,
                activity=activity,
                location="home",
            )
            self.db.insert_character_activity_log(
                character_id=char_id,
                tick_id=tick_id,
                activity=activity,
                time_period=world_state.time_period,
                weather_type=world_state.weather.type,
            )

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "tick_count": self._tick_count,
            "tick_interval": self.tick_interval,
            "phase2_enabled": self._phase2,
            "current_time": datetime.now().isoformat(),
            "world_engine": {
                "time_period": self.world_engine.time_engine.get_time_period(),
                "weather": self.world_engine.weather_engine.current_weather,
            },
        }


# =============================================================================
# 便捷启动函数
# =============================================================================

def start_world(db_path: str = None, block: bool = False,
                enable_phase2: bool = False) -> WorldTick:
    """便捷启动函数：创建 WorldTick 并启动世界循环。

    Args:
        db_path: 数据库路径
        block: 是否阻塞当前线程
        enable_phase2: 是否启用 Phase 2 自主行为链路

    Returns:
        WorldTick 实例
    """
    db = V3Database(db_path) if db_path else V3Database()
    wt = WorldTick(db=db, enable_phase2=enable_phase2)
    wt.start(block=block)
    return wt


if __name__ == "__main__":
    print("=" * 60)
    print("AI-Companion-OS V3 - World Tick 独立测试 (Phase 2)")
    print("=" * 60)

    wt = start_world(block=False, enable_phase2=True)

    for i in range(3):
        result = wt.tick_once()
        ws = result["world_state"]
        print(f"\n--- Tick #{result['tick_id']} ---")
        print(f"时间: {ws.datetime_text} | {ws.time_period}")
        print(f"天气: {ws.weather.label} {ws.weather.temperature}°C")
        print(f"氛围: {ws.environment.atmosphere} | 场景: {ws.get_scene_key()}")

        if "phase2_results" in result:
            for r in result["phase2_results"]:
                d = r["decision"]
                print(f"  [{r['character_id']}] → {d.get('action_type')} "
                      f"(score={d.get('score', 0):.1f}, "
                      f"confidence={d.get('confidence', 0):.2f}, "
                      f"priority={d.get('priority', 0)})")
                time.sleep(0.5)
        time.sleep(1)

    wt.stop()
    print("\n测试完成")
