"""
V3 主入口

提供两种运行模式：
1. 命令行模式：`python -m v3.main --once --phase2` 单次 tick 调试
2. API 模式：`uvicorn v3.main:app` 启动 FastAPI 服务

FastAPI 模式自动启动 APScheduler 和自主行为引擎。
"""

import sys
import time
import argparse
import json
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from .db import V3Database
from .config import (
    TICK_INTERVAL_SECONDS, API_HOST, API_PORT, API_WORKERS,
    ENV, LOG_DIR, LOG_LEVEL,
)

# ── FastAPI app（延迟创建，命令行模式不需要） ──
_app: Optional[object] = None
_world_tick: Optional[object] = None
_life_kernel: Optional[object] = None
_scheduler: Optional[object] = None
_db: Optional[V3Database] = None

# ═════════════════════════════════════════════════════════════
# 数据库 + 角色初始化
# ═════════════════════════════════════════════════════════════

def init_database(db: V3Database):
    """初始化数据库：建表并写入默认数据。"""
    db.connect()
    db.create_tables()
    try:
        db._create_v4_tables()
    except Exception as e:
        print(f"[V3] V4 表创建失败（非致命）: {e}")
    print("[V3] 数据库初始化完成（含 Phase 2 + V4 表）")
    return db


def register_default_characters(db: V3Database):
    """从 V2 角色配置注册角色到 V3 状态表。"""
    from .config import V2_PERSONAS_DIR

    personas_path = Path(V2_PERSONAS_DIR)
    if not personas_path.exists():
        print(f"[V3] V2 角色配置目录不存在: {V2_PERSONAS_DIR}，跳过角色注册")
        return

    yaml_files = list(personas_path.glob("*.yaml")) + list(personas_path.glob("*.yml"))
    if not yaml_files:
        print("[V3] 未找到 YAML 角色配置文件")
        return

    try:
        import yaml
    except ImportError:
        print("[V3] PyYAML 未安装，使用纯文本解析角色ID")
        yaml = None

    for yf in yaml_files:
        try:
            if yaml:
                with open(yf, "r", encoding="utf-8") as f:
                    persona = yaml.safe_load(f)
            else:
                persona = {"id": yf.stem}

            char_id = persona.get("id", yf.stem)
            db.upsert_character_state(
                character_id=char_id,
                activity="idle",
                location="home",
            )
            print(f"[V3] 角色已注册: {char_id}")
        except Exception as e:
            print(f"[V3] 角色注册失败 ({yf.name}): {e}")

    db.conn.commit()


# ═════════════════════════════════════════════════════════════
# 命令行输出
# ═════════════════════════════════════════════════════════════

def print_phase1_tick_result(result: dict):
    """打印 Phase 1 tick 结果摘要。"""
    ws = result["world_state"]
    print(f"\nTick #{result['tick_id']}")
    print(f"  时间: {ws.datetime_text}")
    print(f"  星期: {ws.day_of_week}")
    print(f"  时段: {ws.time_period}")
    print(f"  季节: {ws.season}")
    print(f"  天气: {ws.weather.label} ({ws.weather.type})")
    print(f"  温度: {ws.weather.temperature}°C")
    print(f"  湿度: {ws.weather.humidity}%")
    print(f"  风力: {ws.weather.wind_level} 级")
    print(f"  光线: {ws.environment.light}")
    print(f"  噪音: {ws.environment.noise}")
    print(f"  氛围: {ws.environment.atmosphere}")
    print(f"  场景键: {ws.get_scene_key()}")
    print(f"  全局事件: {len(ws.global_events)}")


def print_phase2_results(results: list):
    """打印 Phase 2 自主决策结果。"""
    if not results:
        print("  [Phase 2] 无角色或决策未触发")
        return

    print(f"\n  ── Phase 2 自主决策 ({len(results)} 角色) ──")
    for r in results:
        d = r["decision"]
        action = d.get("action_type", "UNKNOWN")
        score = d.get("score", 0)
        confidence = d.get("confidence", 0)
        priority = d.get("priority", 0)
        intent = d.get("intent", "")
        target = d.get("target", "")

        bar = "█" * min(int(score / 5), 20) + "░" * max(20 - int(score / 5), 0)
        print(f"  {r['character_id']:12s} | [{bar}] {score:5.1f}")
        print(f"    → {action:20s}  confidence={confidence:.2f}  priority={priority}")
        if intent:
            print(f"    intent={intent:12s}  target={target}")


# ═════════════════════════════════════════════════════════════
# FastAPI 应用
# ═════════════════════════════════════════════════════════════

def create_app(enable_phase2: bool = True):
    """创建 FastAPI app 实例。

    Args:
        enable_phase2: 是否启用 Phase 2 自主行为链路
    """
    global _app, _world_tick, _life_kernel, _scheduler, _db

    try:
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.responses import JSONResponse
        import asyncio
    except ImportError:
        print("[V3] FastAPI 未安装，无法创建 API 服务")
        return None

    app = FastAPI(
        title="AI-Companion-OS V3",
        description="World Simulation Engine with Autonomy",
        version="3.0.0",
    )

    # ── 启动事件 ──
    @app.on_event("startup")
    async def startup():
        global _life_kernel, _scheduler, _db

        from v3.runtime.runtime_state import RuntimeState
        from v3.runtime.event_bus import EventBus
        from v3.runtime.scheduler import Scheduler
        from v3.core.life_kernel import LifeKernel

        _db = V3Database()
        init_database(_db)
        register_default_characters(_db)

        rt = RuntimeState.get_instance()
        rt.life_loop_status = "initializing"
        bus = EventBus.get_instance()

        def start_scheduler(life_loop):
            global _scheduler
            try:
                _scheduler = Scheduler(event_bus=bus, life_loop=life_loop)
                _scheduler.start()
                print("[V3] Scheduler 已启动（1min / 5min / 每日0点）")
            except Exception as e:
                print(f"[V3] Scheduler 启动失败（非致命）: {e}")
                _scheduler = None

        try:
            _life_kernel = LifeKernel(
                event_bus=bus,
                db=_db,
                tick_interval=5,
            )
            _life_kernel.start()
            rt.life_loop_status = "running"
            rt.uptime_start = time.time()
            start_scheduler(_life_kernel)
            print("[V3] LifeKernel 已启动（V4 统一生命内核，interval=5s）")
        except Exception as e:
            _life_kernel = None
            rt.life_loop_status = "error"
            print(f"[V3] LifeKernel 启动失败: {e}")

        print("[V3] V4 全栈启动完成")

    @app.on_event("shutdown")
    async def shutdown():
        global _scheduler, _life_kernel, _world_tick
        if _scheduler:
            _scheduler.stop()
        if _life_kernel:
            _life_kernel.stop()
        if _world_tick:
            _world_tick.stop()
        print("[V3] 服务已停止")

    # ── Health Check ──
    @app.get("/health")
    async def health():
        """服务健康检查。

        Returns:
            {"status":"ok","db":"ok","llm":"ok","world":"ok","life_loop":"ok"}
        """
        health_status = {"status": "ok", "db": "unknown",
                          "llm": "unknown", "world": "unknown",
                          "life_loop": "unknown"}

        # 1. 数据库连接检查
        try:
            if _db and _db.conn:
                cursor = _db._pg_cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                health_status["db"] = "ok"
            else:
                health_status["db"] = "down"
                health_status["status"] = "degraded"
        except Exception:
            health_status["db"] = "down"
            health_status["status"] = "degraded"

        # 2. LLM 配置检查
        try:
            import os
            llm_key = (
                os.environ.get("DEEPSEEK_API_KEY")
                or os.environ.get("QWEN_API_KEY")
                or os.environ.get("OPENAI_API_KEY")
                or os.environ.get("DASHSCOPE_API_KEY")
            )
            if llm_key:
                health_status["llm"] = "ok"
            else:
                health_status["llm"] = "not_configured"
        except Exception:
            health_status["llm"] = "unknown"

        # 3. LifeKernel 运行状态
        try:
            if _life_kernel and getattr(_life_kernel, "state", None):
                from v3.core.life_kernel import KernelState
                if _life_kernel.state == KernelState.RUNNING:
                    health_status["world"] = "ok"
                else:
                    health_status["world"] = _life_kernel.state.value
                    health_status["status"] = "degraded"
            else:
                health_status["world"] = "not_started"
                health_status["status"] = "degraded"
        except Exception:
            health_status["world"] = "error"
            health_status["status"] = "degraded"

        # 4. Life Loop 状态
        try:
            from v3.runtime.runtime_state import RuntimeState
            rt = RuntimeState.get_instance()
            if rt.life_loop_status == "running":
                health_status["life_loop"] = "ok"
            elif rt.life_loop_status == "stopped":
                health_status["life_loop"] = "stopped"
                health_status["status"] = "degraded"
            else:
                health_status["life_loop"] = rt.life_loop_status
        except Exception:
            health_status["life_loop"] = "not_started"

        if health_status["llm"] == "not_configured":
            health_status["status"] = "degraded"

        return health_status

    # ── 世界状态 ──
    @app.get("/api/state")
    async def api_state():
        """返回当前世界/LifeKernel 状态快照。"""
        if not _life_kernel:
            return JSONResponse(
                {"error": "LifeKernel 未启动"}, status_code=503
            )

        recent = _db.get_recent_world_states(1) if _db else []
        return {
            "kernel": {
                "state": _life_kernel.state.value,
                "tick_count": _life_kernel.tick_count,
                "uptime": round(time.time() - _life_kernel.uptime_start, 1)
                if _life_kernel.uptime_start else 0,
            },
            "world_states": recent,
        }

    # ── 角色列表 ──
    @app.get("/api/characters")
    async def api_characters():
        """返回注册的角色列表。"""
        if not _db:
            return JSONResponse(
                {"error": "数据库未连接"}, status_code=503
            )
        chars = _db.get_all_characters()
        return {"count": len(chars) if chars else 0, "characters": chars or []}

    # ── 单次 tick（调试用） ──
    @app.post("/api/tick")
    async def api_tick():
        """手动触发一次 LifeKernel tick。"""
        if not _life_kernel:
            return JSONResponse(
                {"error": "LifeKernel 未启动"}, status_code=503
            )
        return _life_kernel.tick()

    # ── WebSocket ──
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket 端点：接收消息，返回角色回复（骨架）。

        协议：
        - 客户端发送 JSON: {"character_id": "...", "message": "..."}
        - 服务端回复 JSON: {"character_id": "...", "reply": "...", "emotion": "..."}
        """
        await websocket.accept()
        await websocket.send_text(
            json.dumps({"type": "system", "message": "AI-Companion-OS V3 已连接"})
        )

        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                    char_id = msg.get("character_id", "unknown")
                    user_msg = msg.get("message", "")

                    # 骨架：返回占位回复
                    reply = f"[{char_id}] 收到你的消息: {user_msg[:50]}..."
                    await websocket.send_text(json.dumps({
                        "type": "reply",
                        "character_id": char_id,
                        "message": reply,
                        "emotion": "neutral",
                    }))
                except json.JSONDecodeError:
                    await websocket.send_text(
                        json.dumps({"type": "error", "message": "无效 JSON"})
                    )
        except WebSocketDisconnect:
            print("[V3] WebSocket 客户端已断开")
        except Exception:
            print("[V3] WebSocket 异常")

    # ── V4: Memory API ──
    @app.get("/api/memory")
    async def api_memory(character_id: str = None, memory_type: str = None,
                          limit: int = 50):
        """查询角色记忆。

        Query params:
            character_id (optional): 角色 ID，不传则返回全部
            memory_type (optional): session/short/long/core/episodic/emotional/relationship/visual
            limit: 返回数量上限，默认 50
        """
        if not _db:
            return JSONResponse({"error": "数据库未连接"}, status_code=503)
        try:
            if character_id:
                memories = _db.get_memories_by_character(
                    character_id, memory_type, limit
                )
            else:
                # 不传 character_id 则返回所有角色的记忆
                chars = _db.get_all_characters()
                memories = []
                for c in (chars or []):
                    char_mems = _db.get_memories_by_character(
                        c.get("character_id") or c[0], memory_type, min(limit, 10)
                    )
                    memories.extend(char_mems)

            return {
                "count": len(memories),
                "memories": memories,
            }
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # ── V4: Emotion API ──
    @app.get("/api/emotion")
    async def api_emotion(character_id: str = None):
        """查询角色当前情绪状态。

        Query params:
            character_id (optional): 角色 ID，不传则返回全部角色
        """
        if not _db:
            return JSONResponse({"error": "数据库未连接"}, status_code=503)
        try:
            if character_id:
                snap = _db.get_latest_emotion_snapshot(character_id)
                if snap:
                    return {
                        "character_id": character_id,
                        "emotions": json.loads(snap.get("emotions_json", "{}")),
                        "pressures": json.loads(snap.get("pressures_json", "{}")),
                        "dominant": snap.get("dominant", "calm"),
                        "absence_hours": snap.get("absence_hours", 0),
                    }
                return {"character_id": character_id, "emotions": {}, "pressures": {}}
            else:
                chars = _db.get_all_characters()
                result = {}
                for c in (chars or []):
                    cid = c.get("character_id") if isinstance(c, dict) else c[0]
                    snap = _db.get_latest_emotion_snapshot(cid)
                    result[cid] = {
                        "emotions": json.loads(snap.get("emotions_json", "{}")) if snap else {},
                        "pressures": json.loads(snap.get("pressures_json", "{}")) if snap else {},
                        "dominant": snap.get("dominant", "calm") if snap else "calm",
                    }
                return {"characters": result}
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # ── V4: World Calendar API ──
    @app.get("/api/world/calendar")
    async def api_world_calendar(days: int = 30):
        """查询世界日历事件（节日/纪念日）。

        Query params:
            days: 查询未来N天的事件，默认 30
        """
        if not _db:
            return JSONResponse({"error": "数据库未连接"}, status_code=503)
        try:
            from v3.world.calendar_engine import CalendarEngine

            ce = CalendarEngine(db=_db)
            # 检测当前日期的事件
            current_events = ce.check()
            # 查询数据库中的近期事件
            upcoming_db = _db.get_upcoming_calendar_events(days)
            # 预测近期节日
            upcoming_holidays = ce.get_upcoming_events(days)

            return {
                "current": current_events,
                "upcoming_holidays": upcoming_holidays,
                "upcoming_db_events": upcoming_db,
                "current_holiday": ce.get_holiday_name(),
            }
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # ── V4: Life Kernel Status ──
    @app.get("/api/v4/life/status")
    async def api_v4_life_status():
        """V4 LifeKernel 状态查询。

        Returns:
            {"status":"ok","state":"RUNNING","tick_count":N,"uptime":N,"version":"4.0.0"}
        """
        try:
            from v3.runtime.runtime_state import RuntimeState
            rt = RuntimeState.get_instance()
            return {
                "status": "ok",
                "state": rt.life_loop_status,
                "uptime": (time.time() - rt.uptime_start) if rt.uptime_start else 0,
                "version": "4.0.0",
            }
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # ── V4: Desires API ──
    @app.get("/api/v4/desires/{char_id}")
    async def api_v4_desires(char_id: str):
        """查询角色当前欲望值。

        Returns:
            5 维欲望向量：connect / express / avoid / comfort / compete
        """
        if not _db:
            return JSONResponse({"error": "数据库未连接"}, status_code=503)
        try:
            desires = _db.get_desires(char_id)
            return {"character_id": char_id, "desires": desires}
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # ── V4: Social Graph API ──
    @app.get("/api/v4/social")
    async def api_v4_social(char_id: str = None):
        """查询社交关系图。

        Query params:
            char_id (optional): 角色 ID，不传则返回全部关系
        """
        if not _db:
            return JSONResponse({"error": "数据库未连接"}, status_code=503)
        try:
            relations = _db.get_social_relations(char_id)
            # 构建双向图结构
            graph = {}
            for r in relations:
                key = f"{r['from_id']} → {r['to_id']}"
                graph[key] = {
                    "value": r["value"],
                    "type": r["rel_type"],
                }
            return {"relations": graph, "count": len(relations)}
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # ── V4: Visual Profile API ──
    @app.get("/api/v4/visual/profile/{char_id}")
    async def api_v4_visual_profile(char_id: str):
        """查询角色视觉身份档案。

        Returns:
            identity profile JSON（face/body/hair 等固定属性）
        """
        if not _db:
            return JSONResponse({"error": "数据库未连接"}, status_code=503)
        try:
            profile = _db.get_visual_profile(char_id)
            if profile:
                return {
                    "character_id": char_id,
                    "profile": profile.get("profile_data", "{}"),
                }
            return {"character_id": char_id, "profile": "{}", "status": "not_configured"}
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # ── V4: Generate Image API ──
    @app.post("/api/v4/visual/generate")
    async def api_v4_visual_generate(char_id: str, style: str = "selfie",
                                      scene: str = "bedroom"):
        """触发角色图片生成。

        Query params:
            char_id: 角色 ID (required)
            style: selfie / candid / mirror / portrait / full_body
            scene: 场景描述

        Returns:
            {"status":"queued","request_id":"..."}
        """
        if not _db:
            return JSONResponse({"error": "数据库未连接"}, status_code=503)
        try:
            import uuid
            request_id = str(uuid.uuid4())[:8]

            # 获取角色身份档案
            profile = _db.get_visual_profile(char_id)

            # 获取角色当前情绪
            emotions = {}
            try:
                snap = _db.get_latest_emotion_snapshot(char_id)
                if snap:
                    emotions = json.loads(snap.get("emotions_json", "{}"))
            except Exception:
                pass

            # 构建 prompt
            prompt_data = {
                "identity": profile.get("profile_data", "{}") if profile else "{}",
                "emotion": emotions,
                "style": style,
                "scene": scene,
            }

            # 异步生成（骨架：记录请求，实际生成由 image_pipeline 处理）
            _db.insert_album_entry(
                char_id, f"pending:{request_id}",
                prompt=json.dumps(prompt_data, ensure_ascii=False),
                style=style, scene=scene,
            )

            return {
                "status": "queued",
                "request_id": request_id,
                "character_id": char_id,
                "style": style,
                "scene": scene,
            }
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # ── V4: Album API ──
    @app.get("/api/v4/album/{char_id}")
    async def api_v4_album(char_id: str, limit: int = 20):
        """查询角色相册。

        Query params:
            char_id: 角色 ID (required)
            limit: 返回数量上限，默认 20
        """
        if not _db:
            return JSONResponse({"error": "数据库未连接"}, status_code=503)
        try:
            entries = _db.get_album(char_id, limit)
            return {
                "character_id": char_id,
                "count": len(entries),
                "album": entries,
            }
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    _app = app
    return app


def get_app():
    """获取 FastAPI app 实例（供 uvicorn 使用）。"""
    global _app
    if _app is None:
        _app = create_app()
    return _app


# ═════════════════════════════════════════════════════════════
# 命令行入口
# ═════════════════════════════════════════════════════════════

def main():
    """V3 主入口。

    三种运行方式：
    1. python -m v3.main --once --phase2   → 单次调试
    2. python -m v3.main --serve           → FastAPI 模式（不阻塞）
    3. uvicorn v3.main:app                 → 外部 uvicorn
    """
    parser = argparse.ArgumentParser(
        description="AI-Companion-OS V3: World Simulation Engine"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="只执行一次 tick 并输出结果（调试模式）",
    )
    parser.add_argument(
        "--phase2",
        action="store_true",
        help="启用 Phase 2 自主行为全链路（情绪压力/缺席/决策/仲裁/反馈）",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=TICK_INTERVAL_SECONDS,
        help=f"tick 间隔（秒），默认 {TICK_INTERVAL_SECONDS}",
    )
    parser.add_argument(
        "--block",
        action="store_true",
        help="阻塞运行（前台模式，while True 循环）",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="以 FastAPI 模式启动（uvicorn）",
    )
    parser.add_argument(
        "--host",
        default=API_HOST,
        help=f"API 监听地址，默认 {API_HOST}",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=API_PORT,
        help=f"API 监听端口，默认 {API_PORT}",
    )

    args = parser.parse_args()
    mode_label = "Phase 2" if args.phase2 else "Phase 1"

    # ── FastAPI 模式 ──
    if args.serve:
        try:
            import uvicorn
        except ImportError:
            print("[V3] uvicorn 未安装，请 pip install uvicorn")
            sys.exit(1)

        app = create_app(enable_phase2=args.phase2)
        if app is None:
            sys.exit(1)

        print("=" * 60)
        print(f"AI-Companion-OS V3 API Server ({mode_label})")
        print(f"  http://{args.host}:{args.port}")
        print(f"  /health  /api/state  /api/characters  /ws")
        print("=" * 60)

        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            log_level=LOG_LEVEL.lower(),
        )
        return

    # ── 单次调试模式 ──
    if args.once:
        from .world.world_tick import WorldTick

        print("=" * 60)
        print(f"AI-Companion-OS V3 — World Simulation Engine ({mode_label})")
        print("=" * 60)

        db = V3Database()
        init_database(db)
        register_default_characters(db)

        wt = WorldTick(
            db=db,
            tick_interval=args.interval,
            enable_phase2=args.phase2,
            use_scheduler=False,
        )
        db.connect()
        db.create_tables()

        result = wt.tick_once()
        print_phase1_tick_result(result)

        if args.phase2 and "phase2_results" in result:
            print_phase2_results(result["phase2_results"])

        db.close()
        return

    # ── 阻塞循环模式 ──
    from .world.world_tick import WorldTick

    print("=" * 60)
    print(f"AI-Companion-OS V3 — World Simulation Engine ({mode_label})")
    print("=" * 60)

    db = V3Database()
    init_database(db)
    register_default_characters(db)

    wt = WorldTick(
        db=db,
        tick_interval=args.interval,
        enable_phase2=args.phase2,
        use_scheduler=False,
    )
    wt.start(block=args.block)

    print(f"[V3] 世界循环运行中 ({mode_label}, interval={args.interval}s)")
    print("[V3] 按 Ctrl+C 停止")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[V3] 正在停止...")
        wt.stop()
        print("[V3] 已停止")


# 供 uvicorn 直接引用
app = get_app()

if __name__ == "__main__":
    main()
