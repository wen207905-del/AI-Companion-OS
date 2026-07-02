"""Application bootstrap — DB, engines, event bus wiring."""

from __future__ import annotations

import json
import time

from app_state import state
from config import PERSONA_DIR, get_db, init_db
from chat.message_service import ensure_message_schema
from engine.arousal_engine import ArousalEngine
from engine.emotion_engine import EmotionEngine
from engine.boundary_engine import BoundaryEngine
from engine.growth_engine import GrowthEngine
from engine.relationship_engine import RelationshipEngine
from event.event_analyzer import event_analyzer
from event.event_bus import event_bus
from memory.memory_manager import MemoryManager
from personality.persona_loader import PersonaLoader


def init_all() -> None:
    state.persona_loader = PersonaLoader(PERSONA_DIR)

    state.db = get_db()
    init_db(state.db)
    ensure_message_schema(state.db)

    state.rel_engine = RelationshipEngine(state.db)
    state.emo_engine = EmotionEngine(state.db)
    state.memory_manager = MemoryManager(state.db)
    state.growth_engine = GrowthEngine(state.db)
    state.arousal_engine = ArousalEngine(state.db)
    state.boundary_engine = BoundaryEngine()

    for pid, persona in state.persona_loader.personas.items():
        state.rel_engine.init_character(pid, persona)
        state.emo_engine.init_character(pid)
        state.arousal_engine.init_character(pid, persona)
        rel_loaded = state.rel_engine.load_from_db(pid)
        emo_loaded = state.emo_engine.load_from_db(pid)
        arousal_loaded = state.arousal_engine.load_from_db(pid)
        if not rel_loaded:
            state.rel_engine.save_snapshot(pid, "init")
        if not emo_loaded:
            state.emo_engine.save_snapshot(pid, "init")
        if not arousal_loaded:
            state.arousal_engine.save_snapshot(pid, "init")

    if state.rel_engine:
        state.rel_engine.ensure_minimum_love(70.0)

    _sync_group_members_from_db()
    _register_event_handler()


def _sync_group_members_from_db() -> None:
    """从数据库加载各群成员到内存，不再自动创建「全员群」。"""
    db = state.db
    assert db is not None

    cur = db.execute("SELECT chat_id, character_id FROM group_chat_members")
    members_map: dict[str, set[str]] = {}
    for row in cur.fetchall():
        members_map.setdefault(row["chat_id"], set()).add(row["character_id"])
    state.group_members = members_map


def _register_event_handler() -> None:
    db = state.db
    rel_engine = state.rel_engine
    emo_engine = state.emo_engine
    memory_manager = state.memory_manager
    growth_engine = state.growth_engine
    arousal_engine = state.arousal_engine
    persona_loader = state.persona_loader
    assert db is not None and rel_engine is not None and emo_engine is not None

    def _event_handler(event):
        analysis = event_analyzer.analyze(event)

        targets = [p for p in event.participants if p != "user"]
        scope = "group" if len(event.participants) > 2 else "private"
        scope_id = event.metadata.get("group_id") if scope == "group" else None

        for eff in analysis.effects:
            target = eff["target"]
            if eff["engine"] == "relationship":
                rel_engine.apply_effect(target, eff["field"], eff["delta"], event.event_id)
                rel_engine.save_snapshot(target, event.event_id)
            elif eff["engine"] == "emotion":
                emo_engine.apply_effect(target, eff["field"], eff["delta"])
                emo_engine.save_snapshot(target, event.event_id)

        for participant in event.participants:
            if participant == "user":
                continue
            rel = rel_engine.states.get(participant)
            if not rel:
                continue
            love_pull = rel.love / 100
            emo_engine.apply_effect(participant, "happy", love_pull * 2)
            emo_engine.apply_effect(participant, "excited", love_pull * 1.5)
            if rel.trust > 40:
                emo_engine.apply_effect(participant, "calm", 1.2)
            if rel.attachment > 30:
                emo_engine.apply_effect(participant, "lonely", -1.5)
            if rel.jealousy > 25:
                emo_engine.apply_effect(participant, "stressed", rel.jealousy * 0.1)
            emo = emo_engine.states.get(participant)
            if emo and emo.sad > 40:
                rel_engine.apply_effect(participant, "attachment", 0.3, event.event_id)
            if emo and emo.lonely > 50:
                rel_engine.apply_effect(participant, "security", -0.3, event.event_id)

        if growth_engine and event.event_type == "conversation":
            xp = 8 if scope == "private" else 5
            for target in targets:
                growth_engine.add_xp(target, xp)

        if arousal_engine and event.event_type == "conversation" and event.raw_input:
            group_scale = 0.5 if len(event.participants) > 2 else 1.0
            for target in targets:
                rel_sum = rel_engine.get_summary(target)
                emo_sum = emo_engine.get_summary(target)
                arousal_engine.process_message(
                    target,
                    event.raw_input or "",
                    rel_sum,
                    emo_sum,
                    scale=group_scale,
                )
                arousal_engine.save_snapshot(target, event.event_id)

        if memory_manager and event.raw_input and scope == "group" and scope_id:
            from chat.group_memory import record_group_user_message
            record_group_user_message(
                targets,
                group_id=scope_id,
                group_name=event.metadata.get("group_name") or "群聊",
                content=event.raw_input,
                event_id=event.event_id,
            )
        elif memory_manager and analysis.memory_snapshot:
            for target in targets:
                memory_manager.store_from_snapshot(
                    target,
                    analysis.memory_snapshot,
                    scope=scope,
                    scope_id=scope_id,
                    event_id=event.event_id,
                    role="user",
                )

        db.execute(
            """
            INSERT INTO event_log
            (event_id, event_type, timestamp, participants, raw_input,
             analysis_result, memory_snapshot, weight)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.event_type,
                event.timestamp,
                json.dumps(event.participants, ensure_ascii=False),
                event.raw_input,
                json.dumps([eff for eff in analysis.effects], ensure_ascii=False),
                analysis.memory_snapshot,
                event.weight,
            ),
        )
        db.commit()

        if event.event_type == "conversation" and len(event.participants) == 2:
            db.execute(
                """
                INSERT INTO private_messages
                (id, character_id, sender_type, content, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.participants[1],
                    "user",
                    event.raw_input or "",
                    event.timestamp,
                ),
            )
            db.commit()

        return analysis

    event_bus.subscribe("*", _event_handler)
