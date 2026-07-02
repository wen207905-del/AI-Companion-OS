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
_db: Optional[V3Database] = None

# ═════════════════════════════════════════════════════════════
# 数据库 + 角色初始化
# ═════════════════════════════════════════════════════════════

def init_database(db: V3Database):
    """初始化数据库：建表并写入默认数据。"""
    db.connect()
    db.create_tables()
    print("[V3] 数据库初始化完成（含 Phase 2 表）")
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
    global _app, _world_tick, _db

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
        global _world_tick, _db

        from .world.world_tick import WorldTick

        _db = V3Database()
        init_database(_db)
        register_default_characters(_db)

        _world_tick = WorldTick(
            db=_db,
            tick_interval=TICK_INTERVAL_SECONDS,
            enable_phase2=enable_phase2,
            use_scheduler=True,
        )
        _world_tick.db.connect()
        _world_tick.db.create_tables()
        _world_tick.start()
        print("[V3] WorldTick 已启动（APScheduler 模式）")

    @app.on_event("shutdown")
    async def shutdown():
        if _world_tick:
            _world_tick.stop()
        print("[V3] 服务已停止")

    # ── Health Check ──
    @app.get("/health")
    async def health():
        """服务健康检查。

        Returns:
            {"status": "alive", "world_tick_count": <int>}
        """
        tick_count = _world_tick._tick_count if _world_tick else 0
        return {
            "status": "alive",
            "world_tick_count": tick_count,
            "phase2_enabled": enable_phase2,
        }

    # ── 世界状态 ──
    @app.get("/api/state")
    async def api_state():
        """返回当前世界状态快照。

        Returns:
            JSON 包含时间/天气/环境/角色状态
        """
        if not _world_tick:
            return JSONResponse(
                {"error": "WorldTick 未启动"}, status_code=503
            )

        status = _world_tick.get_status()
        ws = _world_tick.world_engine

        return {
            "time": {
                "datetime": status["current_time"],
                "period": ws.time_engine.get_time_period(),
                "season": ws.time_engine.get_season(),
                "day_of_week": ws.time_engine.get_day_of_week(),
            },
            "weather": ws.weather_engine.current_weather,
            "tick": {
                "count": status["tick_count"],
                "running": status["running"],
            },
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
        """手动触发一次 tick，返回结果。"""
        if not _world_tick:
            return JSONResponse(
                {"error": "WorldTick 未启动"}, status_code=503
            )
        result = _world_tick.tick_once()
        return {
            "tick_id": result.get("tick_id"),
            "world_state": {
                "time_period": result["world_state"].time_period,
                "weather": result["world_state"].weather.type,
                "scene_key": result["world_state"].get_scene_key(),
            },
            "phase2_results": result.get("phase2_results", []),
        }

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
