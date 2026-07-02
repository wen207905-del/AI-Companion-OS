"""Character memory storage and lightweight recall for prompt injection."""

from __future__ import annotations

import time
from typing import Any

from config import USER_NAME


def _query_terms(query: str) -> set[str]:
    q = (query or "").strip()
    if not q:
        return set()
    terms = {q}
    for i in range(len(q)):
        for length in (2, 3, 4):
            if i + length <= len(q):
                terms.add(q[i:i + length])
    return terms


def format_memories_block(memories: list[str]) -> str:
    if not memories:
        return ""
    lines = ["【相关记忆——自然融入对话，不要逐条背诵】"]
    for item in memories:
        lines.append(f"- {item}")
    return "\n".join(lines)


class MemoryManager:
    def __init__(self, db) -> None:
        self.db = db

    def store(
        self,
        character_id: str,
        content: str,
        *,
        role: str = "user",
        scope: str = "private",
        scope_id: str | None = None,
        event_id: str | None = None,
        intensity: float = 50.0,
        memory_type: str = "episodic",
    ) -> None:
        text = (content or "").strip()
        if not text or not character_id:
            return
        self.db.execute(
            """
            INSERT INTO character_memories
            (character_id, scope, scope_id, role, content, memory_type, intensity, timestamp, event_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                character_id,
                scope,
                scope_id,
                role,
                text[:500],
                memory_type,
                float(intensity),
                time.time(),
                event_id,
            ),
        )
        self.db.commit()

    def store_from_snapshot(
        self,
        character_id: str,
        snapshot: str,
        *,
        scope: str = "private",
        scope_id: str | None = None,
        event_id: str | None = None,
        role: str = "user",
    ) -> None:
        if snapshot:
            self.store(
                character_id,
                snapshot,
                role=role,
                scope=scope,
                scope_id=scope_id,
                event_id=event_id,
                intensity=55.0,
            )

    def recall(
        self,
        character_id: str,
        query: str,
        limit: int = 5,
        scope: str = "private",
        scope_id: str | None = None,
    ) -> list[str]:
        if scope_id:
            cur = self.db.execute(
                """
                SELECT content, role, timestamp, intensity
                FROM character_memories
                WHERE character_id = ? AND scope = ? AND scope_id = ?
                ORDER BY timestamp DESC
                LIMIT 200
                """,
                (character_id, scope, scope_id),
            )
        else:
            cur = self.db.execute(
                """
                SELECT content, role, timestamp, intensity
                FROM character_memories
                WHERE character_id = ? AND scope = ? AND scope_id IS NULL
                ORDER BY timestamp DESC
                LIMIT 200
                """,
                (character_id, scope),
            )
        rows = cur.fetchall()
        if not rows:
            return []

        terms = _query_terms(query)
        now = time.time()
        scored: list[tuple[float, str]] = []

        for row in rows:
            content = row["content"] or ""
            role = row["role"] or "user"
            if content.startswith("[群聊"):
                formatted = content
            else:
                prefix = USER_NAME if role == "user" else "我"
                formatted = f"{prefix}：{content}"

            score = 0.0
            if terms:
                for term in terms:
                    if term and term in content:
                        score += 1.0
            else:
                score = 0.1

            age_days = max(0, (now - float(row["timestamp"])) / 86400)
            score += max(0, 3.0 - age_days * 0.1)
            score += float(row["intensity"] or 50) / 100.0 * 0.5
            scored.append((score, formatted))

        scored.sort(key=lambda x: x[0], reverse=True)
        if terms and scored[0][0] > 0.5:
            return [s[1] for s in scored[:limit]]

        return [
            (r["content"] if (r["content"] or "").startswith("[群聊")
             else f"{r['role'] == 'user' and USER_NAME or '我'}：{r['content']}")
            for r in rows[:limit]
        ]

    def recent_for_character(
        self,
        character_id: str,
        limit: int = 3,
        scope: str = "private",
        scope_id: str | None = None,
    ) -> list[str]:
        return self.recall(character_id, "", limit=limit, scope=scope, scope_id=scope_id)

    def recall_for_group_prompt(
        self,
        character_id: str,
        query: str,
        group_id: str,
        *,
        limit: int = 6,
    ) -> list[str]:
        """Merge group-scoped and private personal memories for group chat prompts."""
        cur = self.db.execute(
            """
            SELECT content, role, scope, timestamp, intensity
            FROM character_memories
            WHERE character_id = ?
              AND (
                (scope = 'group' AND scope_id = ?)
                OR (scope = 'private' AND scope_id IS NULL)
              )
            ORDER BY timestamp DESC
            LIMIT 100
            """,
            (character_id, group_id),
        )
        rows = cur.fetchall()
        if not rows:
            return []

        terms = _query_terms(query)
        now = time.time()
        scored: list[tuple[float, str, str]] = []

        for row in rows:
            content = (row["content"] or "").strip()
            if not content:
                continue
            role = row["role"] or "user"
            if content.startswith("[群聊"):
                formatted = content
            else:
                prefix = USER_NAME if role == "user" else "我"
                scope_tag = "（私聊）" if row["scope"] == "private" else "（本群）"
                formatted = f"{prefix}{scope_tag}：{content}"

            score = 0.0
            if terms:
                for term in terms:
                    if term and term in content:
                        score += 1.0
            else:
                score = 0.1

            age_hours = max(0, (now - float(row["timestamp"])) / 3600)
            score += max(0, 4.0 - age_hours * 0.15)
            score += float(row["intensity"] or 50) / 100.0 * 0.5
            if row["scope"] == "private" and age_hours < 3:
                score += 1.5
            scored.append((score, formatted, content))

        scored.sort(key=lambda x: x[0], reverse=True)
        seen: set[str] = set()
        results: list[str] = []
        for _, formatted, raw in scored:
            if raw in seen:
                continue
            seen.add(raw)
            results.append(formatted)
            if len(results) >= limit:
                break
        return results
