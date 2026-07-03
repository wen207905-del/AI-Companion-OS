"""Deliver character photos inside natural private chat."""

from __future__ import annotations

import logging
import re
import time
import uuid

from api.ws_hub import hub
from app_state import state
from engine.world_clock import now as world_now
from image.config import SILICONFLOW_API_KEY
from image.intent_detector import (
    character_offers_photo,
    extract_photo_directive,
    should_proactive_share,
    user_requests_photo,
)
from image.orchestrator import ImageEngineError, generate_character_image
from image.scene_parser import parse_image_intent

logger = logging.getLogger(__name__)

_last_photo_ts: dict[str, float] = {}


def strip_reply_photo_tag(reply_content: str) -> tuple[str | None, str]:
    return extract_photo_directive(reply_content)


def _photo_age(character_id: str) -> float:
    last = _last_photo_ts.get(character_id, 0)
    return time.time() - last if last else 9999.0


def _mark_photo_sent(character_id: str) -> None:
    _last_photo_ts[character_id] = time.time()


def _decide_send(
    *,
    character_id: str,
    user_message: str,
    reply_content: str,
    photo_directive: str | None,
    rel_summary: dict | None,
) -> tuple[bool, str, str]:
    """Return (should_send, hint_text, trigger_reason)."""
    if photo_directive:
        return True, photo_directive, "llm_tag"

    if user_requests_photo(user_message):
        hint = user_message
        if reply_content:
            hint = f"{user_message}。{reply_content[:160]}"
        return True, hint, "user_request"

    if character_offers_photo(reply_content) and should_proactive_share(
        rel_summary, last_photo_age=_photo_age(character_id)
    ):
        return True, reply_content, "proactive_share"

    return False, "", ""


async def maybe_deliver_chat_photo(
    room: str,
    *,
    character_id: str,
    user_message: str,
    reply_content: str,
    photo_directive: str | None = None,
    rel_summary: dict | None = None,
) -> dict | None:
    """Generate and push a photo message when chat context calls for it."""
    if not SILICONFLOW_API_KEY:
        return None

    should, hint, trigger = _decide_send(
        character_id=character_id,
        user_message=user_message,
        reply_content=reply_content,
        photo_directive=photo_directive,
        rel_summary=rel_summary,
    )
    if not should:
        return None

    intent = parse_image_intent(hint)
    if user_requests_photo(user_message) and re_selfie(user_message):
        intent["style"] = "selfie"
    if trigger == "proactive_share" and not intent.get("style"):
        intent["style"] = "selfie"

    emo = state.emo_engine.get_summary(character_id) if state.emo_engine else {}
    if not intent.get("emotion") and emo:
        intent["emotion"] = emo.get("primary_mood", "")

    await hub.send_room(room, {
        "type": "image_generating",
        "character_id": character_id,
    })

    try:
        result = await generate_character_image(
            character_id,
            scene=intent["scene"],
            style=intent.get("style") or "",
            outfit="",
            pose=intent.get("pose") or "",
            emotion=intent.get("emotion") or "",
            exposure=intent["exposure"],
            extra=hint[:240],
            priority="quality",
        )
    except ImageEngineError as exc:
        logger.warning("Chat photo failed for %s: %s", character_id, exc)
        await hub.send_room(room, {
            "type": "error",
            "message": f"照片发送失败：{exc}",
        })
        return None

    msg_id = str(uuid.uuid4())
    ts = world_now()
    state.db.execute(
        """INSERT INTO private_messages
           (id, character_id, sender_type, content, content_type, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (msg_id, character_id, "character", result["url"], "image", ts),
    )
    state.db.commit()
    _mark_photo_sent(character_id)

    await hub.send_room(room, {
        "type": "image_ready",
        "message_id": msg_id,
        "character_id": character_id,
        "url": result["url"],
        "model": result.get("model"),
        "route": result.get("route"),
        "trigger": trigger,
    })
    return result


def re_selfie(text: str) -> bool:
    return bool(text and ("自拍" in text or "selfie" in text.lower()))
