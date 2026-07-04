"""Private chat dual-mode helpers."""

from __future__ import annotations

import json
import uuid
from typing import Any, Callable, Awaitable

from app_state import state
from chat.context_builder import boundary_hint_for, memory_block_for, status_block_for
from chat.history_loader import load_private_history
from chat.stream_delivery import deliver_character_reply
from config import USER_NAME
from engine.world_clock import now as world_now
from services.chat_service import build_chat_messages
from services.mode_router import resolve_mode
from services.mode_settings import get_user_mode, set_user_mode
from services.scene_mode_service import generate_scene_response
from services.social_relation_service import enrich_relationship_summary
from services.speaker_resolver import detect_participants


EmitFn = Callable[[dict], Awaitable[None]]


def resolve_private_mode(user_message: str, explicit_mode: str | None) -> str:
    participants = detect_participants(user_message, state.persona_loader)
    default = get_user_mode(state.db) if state.db else "chat"
    return resolve_mode(
        user_message,
        explicit_mode,
        participant_count=len(participants),
        default=default,
    )


def build_private_llm_messages(
    character_id: str,
    persona: dict,
    user_message: str,
    *,
    boundary_hint: str = "",
) -> list[dict[str, str]]:
    rel = enrich_relationship_summary(
        state.db,
        character_id,
        state.rel_engine.get_summary(character_id),
    )
    emo = state.emo_engine.get_summary(character_id)
    style = state.persona_loader.get_chat_style(character_id)
    history = load_private_history(state.db, character_id, limit=30)
    memory_text = memory_block_for(character_id, user_message, scope="private")
    status_text = status_block_for(
        character_id, persona, rel, emo,
        user_message=user_message, scope="private",
    )
    return build_chat_messages(
        character_id,
        persona,
        rel_summary=rel,
        emo_summary=emo,
        chat_style=style,
        history=history,
        memory_text=memory_text,
        boundary_hint=boundary_hint,
        status_text=status_text,
        user_message=user_message,
    )


def format_scene_display(result: dict[str, Any]) -> str:
    lines = [result.get("narration") or ""]
    for ev in result.get("events") or []:
        cid = ev.get("character_id", "")
        name = state.persona_loader.get_display_name(cid) if cid else ""
        if ev.get("action"):
            lines.append(f"【{name}】{ev['action']}")
        if ev.get("dialogue"):
            lines.append(f"{name}：「{ev['dialogue']}」")
    return "\n\n".join(line for line in lines if line.strip())


async def handle_private_scene(
    *,
    room: str,
    character_id: str,
    user_message: str,
    llm_choice: dict | None,
    emit: EmitFn,
) -> None:
    participants = detect_participants(user_message, state.persona_loader)
    if character_id not in participants and character_id:
        participants = [character_id] + [p for p in participants if p != character_id]

    result = await generate_scene_response(
        user_message,
        llm_choice,
        participant_ids=participants or None,
    )
    reply_id = f"scene_{uuid.uuid4().hex[:12]}"
    display = format_scene_display(result)
    ts = world_now()

    state.db.execute(
        """INSERT INTO private_messages
           (id, character_id, sender_type, content, action, inner_thought, content_type, timestamp)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            reply_id,
            character_id,
            "character",
            display,
            json.dumps(result, ensure_ascii=False),
            "",
            "scene",
            ts,
        ),
    )
    state.db.commit()

    await emit({
        "type": "scene_event",
        "id": reply_id,
        "mode": "scene",
        "narration": result.get("narration", ""),
        "participants": result.get("participants", []),
        "events": result.get("events", []),
        "content": display,
        "parse_fallback": result.get("parse_fallback", False),
        "timestamp": ts,
        "character_id": character_id,
    })
