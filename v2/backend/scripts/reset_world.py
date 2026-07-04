#!/usr/bin/env python3
"""清空测试聊天记录，从 persona 配置重建初始世界状态。"""

from __future__ import annotations

import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from config import DB_PATH, PERSONA_DIR, get_db, init_db, load_all_personas  # noqa: E402
from engine.arousal_engine import ArousalEngine  # noqa: E402
from engine.emotion_engine import EmotionEngine  # noqa: E402
from engine.growth_engine import GrowthEngine  # noqa: E402
from engine.relationship_engine import RelationshipEngine  # noqa: E402
from personality.persona_loader import PersonaLoader  # noqa: E402
from services.social_relation_service import seed_all_characters  # noqa: E402

TABLES = (
    "private_messages",
    "group_messages",
    "group_chat_members",
    "group_chats",
    "character_memories",
    "diary_entries",
    "timeline_events",
    "event_log",
    "relationship_snapshot",
    "emotion_snapshot",
    "arousal_snapshot",
    "character_growth",
    "chat_llm_prefs",
    "character_user_relation",
)


def _remove_db_files() -> None:
    for path in (DB_PATH, Path(f"{DB_PATH}-wal"), Path(f"{DB_PATH}-shm")):
        if path.exists():
            path.unlink()
            print(f"[reset] 已删除 {path}")


def _seed_initial_state(conn) -> None:
    loader = PersonaLoader(PERSONA_DIR)
    rel = RelationshipEngine(conn)
    emo = EmotionEngine(conn)
    arousal = ArousalEngine(conn)
    growth = GrowthEngine(conn)

    for pid, persona in loader.personas.items():
        rel.init_character(pid, persona)
        emo.init_character(pid)
        arousal.init_character(pid, persona)

    seeded = seed_all_characters(rel, conn, list(loader.personas.keys()), force=True)
    print(f"[reset] V4.1 关系初始化：{seeded} 个角色（来自 relationship_init.yaml）")

    for pid in loader.personas.keys():
        rel.save_snapshot(pid, "init")
        emo.save_snapshot(pid, "init")
        arousal.save_snapshot(pid, "init")
        growth._ensure_row(pid)

    conn.commit()
    loves = [rel.states[p].love for p in loader.personas.keys() if p in rel.states]
    print(f"[reset] 已初始化 {len(loader.personas)} 个角色，好感范围 {min(loves):.0f}–{max(loves):.0f}")


def main() -> None:
    print("[reset] 开始重置世界状态…")
    _remove_db_files()
    conn = get_db()
    init_db(conn)
    _seed_initial_state(conn)
    conn.close()
    print("[reset] 完成 — 聊天记录已清空，角色已回归初始状态")
    print("[reset] 重要：请重启 API 使运行中的服务重新加载数据库：")
    print("[reset]   docker compose restart api")


if __name__ == "__main__":
    main()
