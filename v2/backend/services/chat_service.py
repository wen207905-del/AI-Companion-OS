"""V4.1 chat mode — action + dialogue structured replies."""

from __future__ import annotations

from typing import Any

from app_state import state
from chat.prompt_builder import PromptBuilder
from services.social_relation_service import enrich_relationship_summary


def build_chat_messages(
    character_id: str,
    persona: dict,
    *,
    rel_summary: dict[str, Any],
    emo_summary: dict[str, Any],
    chat_style: dict[str, Any],
    history: list[dict[str, str]],
    memory_text: str = "",
    boundary_hint: str = "",
    status_text: str = "",
    user_message: str = "",
) -> list[dict[str, str]]:
    if state.db is not None:
        rel_summary = enrich_relationship_summary(state.db, character_id, rel_summary)

    recent_memories = memory_text.strip() or "（暂无）"
    builder = PromptBuilder(persona)
    return builder.build_chat_mode_messages(
        rel_summary,
        emo_summary,
        chat_style,
        history,
        memory_text=memory_text,
        boundary_hint=boundary_hint,
        status_text=status_text,
        user_message=user_message,
        recent_memories=recent_memories,
    )
