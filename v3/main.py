"""
V3 主入口

启动 World Tick 循环，初始化各引擎，提供命令行接口。
支持 --phase2 启用 Phase 2 自主行为全链路。
"""

import sys
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from .db import V3Database
from .world import WorldTick, start_world
from .config import TICK_INTERVAL_SECONDS


def init_database(db: V3Database):
    """初始化数据库：建表并写入默认数据。"""
    db.connect()
    db.create_tables()
    print("[V3] 数据库初始化完成（含 Phase 2 表）")
    return db


def register_default_characters(db: V3Database):
    """从 V2 角色配置注册角色到 V3 状态表。"""
    from .config import V2_PERSONAS_DIR
    import os

    personas_path = Path(V2_PERSONAS_DIR)
    if not personas_path.exists():
        print(f"[V3] V2 角色配置目录不存在: {V2_PERSONAS_DIR}，跳过角色注册")
        return

    yaml_files = list(personas_path.glob("*.yaml")) + list(personas_path.glob("*.yml"))
    if not yaml_files:
        print(f"[V3] 未找到 YAML 角色配置文件")
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

        bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
        print(f"  {r['character_id']:12s} | [{bar}] {score:5.1f}")
        print(f"    → {action:20s}  confidence={confidence:.2f}  priority={priority}")
        if intent:
            print(f"    intent={intent:12s}  target={target}")


def main():
    """V3 主入口。"""
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
        help="阻塞运行（前台模式）",
    )

    args = parser.parse_args()

    mode_label = "Phase 2" if args.phase2 else "Phase 1"
    print("=" * 60)
    print(f"AI-Companion-OS V3 — World Simulation Engine ({mode_label})")
    print("=" * 60)

    db = V3Database()
    init_database(db)
    register_default_characters(db)

    if args.once:
        wt = WorldTick(db=db, tick_interval=args.interval,
                       enable_phase2=args.phase2)
        db.connect()
        db.create_tables()

        result = wt.tick_once()
        print_phase1_tick_result(result)

        if args.phase2 and "phase2_results" in result:
            print_phase2_results(result["phase2_results"])

        db.close()
        return

    wt = start_world(block=args.block, enable_phase2=args.phase2)
    print(f"[V3] 世界循环运行中 ({mode_label}, interval={args.interval}s)")
    print("[V3] 按 Ctrl+C 停止")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[V3] 正在停止...")
        wt.stop()
        print("[V3] 已停止")


if __name__ == "__main__":
    main()
