"""Persistent event log backed by SQLite."""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("companion.event_log")


class EventLog:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def initialize(self) -> None:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS event_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                character_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload TEXT DEFAULT '{}'
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_event_char ON event_log(character_id, timestamp)")
        conn.commit()
        conn.close()

    async def record(self, event: dict[str, Any]) -> int:
        conn = sqlite3.connect(self._db_path)
        ts = time.time()
        cursor = conn.execute(
            "INSERT INTO event_log (timestamp, character_id, event_type, payload) VALUES (?, ?, ?, ?)",
            (ts, event["character_id"], event["event_type"], json.dumps(event.get("payload", {}), ensure_ascii=False)),
        )
        conn.commit()
        row_id = cursor.lastrowid
        conn.close()
        return row_id

    async def query(self, character_id: str, limit: int = 50) -> list[dict[str, Any]]:
        conn = sqlite3.connect(self._db_path)
        rows = conn.execute(
            "SELECT id, timestamp, character_id, event_type, payload FROM event_log WHERE character_id = ? ORDER BY timestamp DESC LIMIT ?",
            (character_id, limit),
        ).fetchall()
        conn.close()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "character_id": r[2],
                "event_type": r[3],
                "payload": json.loads(r[4]),
            }
            for r in rows
        ]
