"""Shared application state — initialized once at startup."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import sqlite3

    from engine.emotion_engine import EmotionEngine
    from engine.relationship_engine import RelationshipEngine
    from personality.persona_loader import PersonaLoader


class AppState:
    db: sqlite3.Connection | None = None
    rel_engine: RelationshipEngine | None = None
    emo_engine: EmotionEngine | None = None
    persona_loader: PersonaLoader | None = None
    memory_manager: Any = None
    growth_engine: Any = None
    arousal_engine: Any = None
    boundary_engine: Any = None
    group_members: dict[str, set[str]] = {}


state = AppState()
