"""Assemble memory and boundary context for LLM prompts."""

from __future__ import annotations

from app_state import state
from chat.history_loader import load_recent_private_bridge
from memory.memory_manager import format_memories_block


def memory_block_for(
    character_id: str,
    query: str,
    scope: str = "private",
    scope_id: str | None = None,
) -> str:
    if not state.memory_manager:
        return ""
    memories = state.memory_manager.recall(
        character_id, query, limit=5, scope=scope, scope_id=scope_id,
    )
    return format_memories_block(memories)


def memory_block_for_group(
    character_id: str,
    query: str,
    group_id: str,
) -> str:
    """
    Group chat memory: merge group memories + private personal memories,
    plus recent private message transcript for topic continuity.
    """
    parts: list[str] = []

    bridge = ""
    if state.db and state.persona_loader:
        char_name = state.persona_loader.get_display_name(character_id)
        bridge = load_recent_private_bridge(state.db, character_id, char_name)
    if bridge:
        parts.append(bridge)

    if state.memory_manager:
        merged = state.memory_manager.recall_for_group_prompt(
            character_id, query, group_id, limit=6,
        )
        mem_block = format_memories_block(merged)
        if mem_block:
            parts.append(mem_block)

    return "\n\n".join(parts)


def boundary_hint_for(persona: dict, user_message: str, character_id: str) -> str:
    if not state.boundary_engine:
        return ""
    evaluation = state.boundary_engine.evaluate(persona, user_message)
    if evaluation.get("level") != "ok" and state.emo_engine and state.rel_engine:
        state.boundary_engine.apply_emotion_effects(
            character_id,
            evaluation,
            state.emo_engine,
            state.rel_engine,
            event_id="boundary",
        )
    return evaluation.get("prompt_hint", "")


def status_block_for(
    character_id: str,
    persona: dict,
    rel_summary: dict,
    emo_summary: dict,
    *,
    user_message: str = "",
    scope: str = "private",
    group_name: str = "",
) -> str:
    """Comprehensive status mod block (V4/V5), empty when mod disabled."""
    from mod.status_block import build_status_block

    arousal_summary = None
    growth_summary = None
    if state.arousal_engine:
        arousal_summary = state.arousal_engine.get_summary(character_id)
    if state.growth_engine:
        growth_summary = state.growth_engine.get_profile(character_id)

    return build_status_block(
        character_id,
        persona,
        rel_summary,
        emo_summary,
        user_message=user_message,
        arousal_summary=arousal_summary,
        growth_summary=growth_summary,
        scope=scope,
        group_name=group_name,
    )
