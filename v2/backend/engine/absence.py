"""Track user absence per character for emotion and proactive behavior."""

from __future__ import annotations

import json
import time


def hours_since_last_user_message(db, character_id: str) -> float:
    row = db.execute(
        """
        SELECT timestamp FROM private_messages
        WHERE character_id = ? AND sender_type = 'user'
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (character_id,),
    ).fetchone()
    if not row:
        return 9999.0
    return max(0.0, (time.time() - float(row["timestamp"])) / 3600.0)


def hours_since_last_interaction(db, character_id: str) -> float:
    row = db.execute(
        """
        SELECT timestamp FROM private_messages
        WHERE character_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (character_id,),
    ).fetchone()
    if not row:
        return 9999.0
    return max(0.0, (time.time() - float(row["timestamp"])) / 3600.0)


def hours_since_last_proactive(db, character_id: str) -> float:
    row = db.execute(
        """
        SELECT timestamp FROM private_messages
        WHERE character_id = ? AND sender_type = 'character'
          AND id LIKE 'pro_%'
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (character_id,),
    ).fetchone()
    if not row:
        return 9999.0
    return max(0.0, (time.time() - float(row["timestamp"])) / 3600.0)


def count_proactive_in_last_hour(db) -> int:
    cutoff = time.time() - 3600.0
    row = db.execute(
        """
        SELECT COUNT(DISTINCT character_id) AS cnt
        FROM private_messages
        WHERE sender_type = 'character'
          AND id LIKE 'pro_%'
          AND timestamp >= ?
        """,
        (cutoff,),
    ).fetchone()
    return int(row["cnt"] or 0) if row else 0


def recent_proactive_texts(db, *, hours: float = 24.0) -> list[str]:
    cutoff = time.time() - hours * 3600.0
    rows = db.execute(
        """
        SELECT content FROM private_messages
        WHERE sender_type = 'character'
          AND id LIKE 'pro_%'
          AND timestamp >= ?
        ORDER BY timestamp DESC
        LIMIT 50
        """,
        (cutoff,),
    ).fetchall()
    return [(r["content"] or "").strip() for r in rows if (r["content"] or "").strip()]


def last_proactive_intent(db, character_id: str) -> tuple[str | None, float]:
    row = db.execute(
        """
        SELECT action, timestamp FROM private_messages
        WHERE character_id = ? AND sender_type = 'character'
          AND id LIKE 'pro_%'
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (character_id,),
    ).fetchone()
    if not row:
        return None, 9999.0

    intent = None
    raw = row["action"]
    if raw:
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(data, dict):
                intent = data.get("intent")
        except (json.JSONDecodeError, TypeError):
            pass

    age = max(0.0, (time.time() - float(row["timestamp"])) / 3600.0)
    return intent, age


def has_unanswered_user_message(db, character_id: str) -> bool:
    row = db.execute(
        """
        SELECT sender_type FROM private_messages
        WHERE character_id = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (character_id,),
    ).fetchone()
    return bool(row and row["sender_type"] == "user")


def has_recent_user_memory(db, character_id: str, *, hours: float = 2.0) -> bool:
    cutoff = time.time() - hours * 3600.0
    row = db.execute(
        """
        SELECT 1 FROM character_memories
        WHERE character_id = ?
          AND role = 'user'
          AND scope = 'private'
          AND timestamp >= ?
        LIMIT 1
        """,
        (character_id, cutoff),
    ).fetchone()
    if row:
        return True

    row = db.execute(
        """
        SELECT 1 FROM private_messages
        WHERE character_id = ? AND sender_type = 'user'
          AND timestamp >= ?
        LIMIT 1
        """,
        (character_id, cutoff),
    ).fetchone()
    return bool(row)


def proactive_context(db, character_id: str) -> dict:
    """Bundle absence metrics for proactive scoring."""
    return {
        "hours_since_user": hours_since_last_user_message(db, character_id),
        "hours_since_proactive": hours_since_last_proactive(db, character_id),
        "hours_since_interaction": hours_since_last_interaction(db, character_id),
        "has_unanswered_user": has_unanswered_user_message(db, character_id),
        "has_recent_user_memory": has_recent_user_memory(db, character_id),
        "hourly_proactive_count": count_proactive_in_last_hour(db),
    }
