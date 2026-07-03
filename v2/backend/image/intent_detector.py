"""Detect photo-sharing intent from chat messages."""

from __future__ import annotations

import re

PHOTO_TAG_RE = re.compile(r"\[PHOTO:([^\]]+)\]", re.IGNORECASE)

USER_REQUEST_PATTERNS = (
    r"发(张|个|一张)?(自拍|照片|图)",
    r"(给|让).{0,6}(看|瞧).{0,8}(照片|自拍|图|样子)",
    r"(自拍|照片|pics?|photo|selfie)",
    r"拍(张|个|一张)?(照|自拍)",
    r"看看你现在",
    r"想看你",
    r"发我看看",
)

CHARACTER_SHARE_PATTERNS = (
    r"给你看",
    r"发给你",
    r"刚拍",
    r"自拍一张",
    r"拍好了",
    r"你看(这张|这张)?",
    r"发张",
    r"分享给你",
    r"给你发",
)


def extract_photo_directive(text: str) -> tuple[str | None, str]:
    """Pull [PHOTO:...] tag from LLM reply and return cleaned text."""
    if not text:
        return None, text or ""
    match = PHOTO_TAG_RE.search(text)
    if not match:
        return None, text.strip()
    directive = match.group(1).strip()
    cleaned = PHOTO_TAG_RE.sub("", text).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return directive, cleaned


def user_requests_photo(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    for pattern in USER_REQUEST_PATTERNS:
        if re.search(pattern, text, re.I) or re.search(pattern, lower, re.I):
            return True
    return False


def character_offers_photo(text: str) -> bool:
    if not text:
        return False
    for pattern in CHARACTER_SHARE_PATTERNS:
        if re.search(pattern, text, re.I):
            return True
    return False


def should_proactive_share(rel_summary: dict | None, *, last_photo_age: float) -> bool:
    """Character voluntarily shares — needs intimacy + cooldown."""
    if last_photo_age < 90:
        return False
    rel = rel_summary or {}
    love = float(rel.get("love") or 0)
    stage = int(rel.get("stage") or 1)
    if stage >= 5 or love >= 78:
        return True
    if stage >= 4 or love >= 70:
        return last_photo_age >= 180
    return False
