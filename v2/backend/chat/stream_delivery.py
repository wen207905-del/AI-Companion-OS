"""WebSocket delivery for character replies (streaming or batch)."""

from __future__ import annotations

from typing import Any, Callable

from app_state import state
from engine.world_clock import now as world_now
from api.ws_hub import hub
from chat.reply_service import generate_reply
from config import LLM_STREAM
from image.chat_photo import maybe_deliver_chat_photo, strip_reply_photo_tag


async def deliver_character_reply(
    room: str,
    *,
    reply_id: str,
    llm_messages: list,
    persona: dict,
    rel_summary: dict | None,
    llm_choice: dict | None,
    ws_meta: dict[str, Any],
    save_to_db: Callable[[str, str, dict, str, float], None],
    memory_scope: str = "private",
    memory_scope_id: str | None = None,
    present_members: list[str] | None = None,
    group_name: str | None = None,
) -> str:
    """
    Generate a character reply and push over WebSocket to all clients in room.
    ws_meta: fields echoed in stream_start/stream_end (character_id, sender_id, etc.)
    Returns final content (may be empty).
    """
    char_name = persona.get("name", persona.get("id", "角色"))

    user_message = ""
    for msg in reversed(llm_messages):
        if msg.get("role") == "user":
            user_message = (msg.get("content") or "").strip()
            break
    chat_mode = "group" if memory_scope == "group" else "private"

    if LLM_STREAM:
        ts = world_now()
        await hub.send_room(room, {
            "type": "stream_start",
            "id": reply_id,
            "character_name": char_name,
            "timestamp": ts,
            **ws_meta,
        })

        async def on_delta(delta: str) -> None:
            await hub.send_room(room, {
                "type": "stream_delta",
                "id": reply_id,
                "delta": delta,
            })

        reply_content, action, inner_thought = await generate_reply(
            llm_messages,
            persona,
            rel_summary=rel_summary,
            llm_choice=llm_choice,
            on_delta=on_delta,
            chat_mode=chat_mode,
            user_message=user_message,
            group_name=group_name or "",
        )
    else:
        reply_content, action, inner_thought = await generate_reply(
            llm_messages,
            persona,
            rel_summary=rel_summary,
            llm_choice=llm_choice,
            chat_mode=chat_mode,
            user_message=user_message,
            group_name=group_name or "",
        )

    photo_directive, reply_content = strip_reply_photo_tag(reply_content or "")

    ts = world_now()
    if reply_content:
        save_to_db(reply_id, reply_content, action, inner_thought, ts)
        char_id = ws_meta.get("character_id") or ws_meta.get("sender_id")
        if (
            memory_scope == "group"
            and memory_scope_id
            and present_members
            and char_id
            and state.memory_manager
        ):
            from chat.group_memory import record_group_character_message
            record_group_character_message(
                present_members,
                group_id=memory_scope_id,
                group_name=group_name or "群聊",
                speaker_id=char_id,
                speaker_name=char_name,
                content=reply_content,
                event_id=reply_id,
            )
        elif char_id and state.memory_manager:
            state.memory_manager.store(
                char_id,
                reply_content,
                role="character",
                scope=memory_scope,
                scope_id=memory_scope_id,
                event_id=reply_id,
                intensity=60.0,
            )

    if LLM_STREAM:
        await hub.send_room(room, {
            "type": "stream_end",
            "id": reply_id,
            "content": reply_content,
            "action": action,
            "inner_thought": inner_thought,
            "timestamp": ts,
            "character_name": char_name,
            **ws_meta,
        })
    elif reply_content:
        await hub.send_room(room, {
            "type": "message",
            "id": reply_id,
            "content": reply_content,
            "action": action,
            "inner_thought": inner_thought,
            "timestamp": ts,
            "character_name": char_name,
            **ws_meta,
        })

    char_id = ws_meta.get("character_id") or ws_meta.get("sender_id")
    if memory_scope == "private" and char_id:
        await maybe_deliver_chat_photo(
            room,
            character_id=char_id,
            user_message=user_message,
            reply_content=reply_content or "",
            photo_directive=photo_directive,
            rel_summary=rel_summary,
        )

    return reply_content or ""
