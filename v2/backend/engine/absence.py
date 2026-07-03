"""Track user absence per character for emotion and proactive behavior."""

from __future__ import annotations

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
