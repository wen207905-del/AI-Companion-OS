"""Group reply post-generation guards: speaker prefix, mismatch, same-turn dedup."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from services.anti_repeat_service import is_too_similar

logger = logging.getLogger("companion.group_guard")

_PREFIX_RE = re.compile(r"^[\s　]*([^：:\n]{1,24})\s*[：:]\s*")


@dataclass
class GuardResult:
    ok: bool
    content: str
    reason: str = ""


def _strip_own_name_prefix(content: str, own_name: str) -> str:
    text = (content or "").lstrip()
    if not own_name:
        return text
    for sep in ("：", ":"):
        prefix = f"{own_name}{sep}"
        if text.startswith(prefix):
            return text[len(prefix):].lstrip()
    return text


def _leading_speaker_name(content: str) -> str | None:
    m = _PREFIX_RE.match(content or "")
    if not m:
        return None
    return (m.group(1) or "").strip() or None


def sanitize_group_reply(
    content: str,
    *,
    own_name: str,
    other_member_names: list[str],
    prior_reply_texts: list[str] | None = None,
    similarity_threshold: float = 0.72,
) -> GuardResult:
    """
    Clean and validate a group reply before save/broadcast.

    - Strip own name prefix
    - Reject if body starts with another member's name (speaker_mismatch)
    - Reject if too similar to an earlier reply in the same turn
    """
    text = _strip_own_name_prefix(content or "", own_name)
    if not text.strip():
        return GuardResult(ok=False, content="", reason="empty_after_strip")

    leading = _leading_speaker_name(text)
    if leading:
        others = {n.strip() for n in other_member_names if n and n.strip()}
        # Exact or "Name：" style match against other members
        if leading in others or any(
            leading == n or leading.startswith(n) or n.startswith(leading)
            for n in others
            if len(n) >= 2
        ):
            logger.info(
                "speaker_mismatch: own=%s leading=%s others=%s",
                own_name,
                leading,
                sorted(others),
            )
            return GuardResult(ok=False, content=text, reason="speaker_mismatch")

    if prior_reply_texts and is_too_similar(
        text, prior_reply_texts, threshold=similarity_threshold,
    ):
        logger.info("same_turn_duplicate blocked for %s", own_name)
        return GuardResult(ok=False, content=text, reason="same_turn_duplicate")

    return GuardResult(ok=True, content=text, reason="")


def wants_multi_responder(user_message: str, member_names: list[str] | None = None) -> bool:
    """True when user explicitly asks multiple people / everyone to reply."""
    text = (user_message or "").strip()
    if not text:
        return False
    broadcast_markers = (
        "大家都",
        "所有人",
        "全员",
        "@所有人",
        "@大家",
        "每人",
        "每个人",
        "一起回答",
        "都来说",
        "都说说",
        "都回一下",
        "都回答",
    )
    if any(m in text for m in broadcast_markers):
        return True

    names = [n for n in (member_names or []) if n]
    if len(names) < 2:
        # Multiple @ mentions without resolved names still count
        return text.count("@") >= 2

    mentioned = sum(1 for n in names if f"@{n}" in text or n in text)
    # Require explicit @ for at least two distinct members when using names
    at_mentioned = sum(1 for n in names if f"@{n}" in text)
    return at_mentioned >= 2 or (text.count("@") >= 2 and mentioned >= 2)
