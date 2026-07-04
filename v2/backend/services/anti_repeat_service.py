"""Detect repetitive proactive share phrasing within 24h."""

from __future__ import annotations

import re
from difflib import SequenceMatcher


def normalize_text(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"[\s\u3000]+", "", t)
    t = re.sub(r"[，。！？!?、；;：:\"'「」『』（）()【】\[\]…\.]+", "", t)
    return t


def similarity(a: str, b: str) -> float:
    na, nb = normalize_text(a), normalize_text(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def is_too_similar(
    text: str,
    recent_texts: list[str],
    *,
    threshold: float = 0.7,
) -> bool:
    for prev in recent_texts:
        if similarity(text, prev) >= threshold:
            return True
    return False


def max_similarity(text: str, recent_texts: list[str]) -> float:
    if not recent_texts:
        return 0.0
    return max(similarity(text, prev) for prev in recent_texts)


def contains_forbidden(text: str, phrases: list[str]) -> bool:
    raw = (text or "").strip()
    if not raw:
        return True
    for phrase in phrases:
        if phrase and phrase in raw:
            return True
    return False
