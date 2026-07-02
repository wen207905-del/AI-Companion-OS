"""Character XP, levels, and milestone tracking."""

from __future__ import annotations

import json
import time
from typing import Any


class GrowthEngine:
    def __init__(self, db) -> None:
        self.db = db

    def _ensure_row(self, character_id: str) -> None:
        cur = self.db.execute(
            "SELECT character_id FROM character_growth WHERE character_id = ?",
            (character_id,),
        )
        if cur.fetchone() is None:
            self.db.execute(
                """
                INSERT INTO character_growth (character_id, xp, level, milestones, updated_at)
                VALUES (?, 0, 1, '[]', ?)
                """,
                (character_id, time.time()),
            )
            self.db.commit()

    def add_xp(self, character_id: str, amount: int) -> dict[str, Any]:
        self._ensure_row(character_id)
        cur = self.db.execute(
            "SELECT xp, level, milestones FROM character_growth WHERE character_id = ?",
            (character_id,),
        )
        row = cur.fetchone()
        xp = int(row["xp"]) + max(0, amount)
        level = int(row["level"])
        milestones = json.loads(row["milestones"] or "[]")
        new_level = 1 + xp // 100
        leveled_up = new_level > level
        if leveled_up:
            level = new_level
            milestone = f"达到等级 {level}"
            if milestone not in milestones:
                milestones.append(milestone)
        self.db.execute(
            """
            UPDATE character_growth
            SET xp = ?, level = ?, milestones = ?, updated_at = ?
            WHERE character_id = ?
            """,
            (xp, level, json.dumps(milestones, ensure_ascii=False), time.time(), character_id),
        )
        self.db.commit()
        return {
            "character_id": character_id,
            "xp": xp,
            "level": level,
            "milestones": milestones,
            "leveled_up": leveled_up,
        }

    def unlock_milestone(self, character_id: str, milestone: str) -> None:
        if not milestone:
            return
        self._ensure_row(character_id)
        profile = self.get_profile(character_id)
        milestones = profile.get("milestones", [])
        if milestone not in milestones:
            milestones.append(milestone)
            self.db.execute(
                """
                UPDATE character_growth
                SET milestones = ?, updated_at = ?
                WHERE character_id = ?
                """,
                (json.dumps(milestones, ensure_ascii=False), time.time(), character_id),
            )
            self.db.commit()

    def get_profile(self, character_id: str) -> dict[str, Any]:
        self._ensure_row(character_id)
        cur = self.db.execute(
            "SELECT xp, level, milestones FROM character_growth WHERE character_id = ?",
            (character_id,),
        )
        row = cur.fetchone()
        milestones = json.loads(row["milestones"] or "[]")
        xp = int(row["xp"])
        level = int(row["level"])
        return {
            "character_id": character_id,
            "xp": xp,
            "level": level,
            "milestones": milestones,
            "xp_to_next": max(0, (level * 100) - xp),
        }
