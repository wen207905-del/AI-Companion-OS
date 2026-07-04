"""User runtime mode persistence."""

from __future__ import annotations

import time

DEFAULT_USER = "default"


def get_user_mode(db, user_id: str = DEFAULT_USER) -> str:
    row = db.execute(
        "SELECT current_mode FROM user_runtime_settings WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        return "chat"
    mode = row["current_mode"] or "chat"
    return mode if mode in ("chat", "scene") else "chat"


def set_user_mode(
    db,
    mode: str,
    *,
    user_id: str = DEFAULT_USER,
    active_character_id: str | None = None,
) -> str:
    if mode not in ("chat", "scene"):
        mode = "chat"
    db.execute(
        """
        INSERT INTO user_runtime_settings (user_id, current_mode, active_character_id, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            current_mode = excluded.current_mode,
            active_character_id = COALESCE(excluded.active_character_id, user_runtime_settings.active_character_id),
            updated_at = excluded.updated_at
        """,
        (user_id, mode, active_character_id, time.time()),
    )
    db.commit()
    return mode
