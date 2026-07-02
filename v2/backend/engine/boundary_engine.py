"""Persona taboo evaluation — character reacts to boundary triggers."""

import re

from config import USER_NAME
from typing import Any


def _taboo_keywords(taboo_line: str) -> list[str]:
    line = (taboo_line or "").strip()
    if not line:
        return []
    parts = re.split(r"[，,、；;。！!？?：:]+", line)
    keywords = [p.strip() for p in parts if len(p.strip()) >= 2]
    if not keywords and len(line) >= 2:
        keywords = [line[:20]]
    return keywords[:6]


def _matches_taboo(message: str, taboo_line: str) -> bool:
    line = (taboo_line or "").strip()
    if not line or not message:
        return False
    if line in message:
        return True
    for i in range(len(line)):
        for length in (2, 3, 4, 5):
            if i + length <= len(line):
                chunk = line[i:i + length]
                if chunk in message:
                    return True
    return False


class BoundaryEngine:
    """Match user messages against persona red/yellow taboos."""

    def evaluate(self, persona: dict[str, Any], message: str) -> dict[str, Any]:
        text = (message or "").strip()
        taboos = persona.get("taboos", {}) or {}
        red_hits: list[str] = []
        yellow_hits: list[str] = []

        for item in taboos.get("red", []) or []:
            if _matches_taboo(text, str(item)):
                red_hits.append(str(item))

        for item in taboos.get("yellow", []) or []:
            if _matches_taboo(text, str(item)):
                yellow_hits.append(str(item))

        level = "red" if red_hits else ("yellow" if yellow_hits else "ok")
        prompt_hint = ""
        if level == "red":
            prompt_hint = (
                f"【底线触发——{USER_NAME}刚才的话严重触碰了你的绝对禁忌："
                + "；".join(red_hits[:2])
                + "。你必须以角色真实反应回应：生气、受伤、冷淡或拒绝，不要装作没事。】"
            )
        elif level == "yellow":
            prompt_hint = (
                f"【不适触发——{USER_NAME}的话让你不太舒服："
                + "；".join(yellow_hits[:2])
                + "。可以别扭、冷淡或委婉表达不满，符合性格即可。】"
            )

        return {
            "level": level,
            "red": red_hits,
            "yellow": yellow_hits,
            "prompt_hint": prompt_hint,
        }

    def apply_emotion_effects(
        self,
        character_id: str,
        evaluation: dict[str, Any],
        emo_engine,
        rel_engine,
        event_id: str = "boundary",
    ) -> None:
        level = evaluation.get("level", "ok")
        if level == "red":
            emo_engine.apply_effect(character_id, "angry", 18)
            emo_engine.apply_effect(character_id, "sad", 8)
            rel_engine.apply_effect(character_id, "trust", -3, event_id)
            rel_engine.apply_effect(character_id, "security", -5, event_id)
            rel_engine.save_snapshot(character_id, event_id)
            emo_engine.save_snapshot(character_id, event_id)
        elif level == "yellow":
            emo_engine.apply_effect(character_id, "stressed", 10)
            emo_engine.apply_effect(character_id, "sad", 5)
            rel_engine.apply_effect(character_id, "security", -2, event_id)
            rel_engine.save_snapshot(character_id, event_id)
            emo_engine.save_snapshot(character_id, event_id)
