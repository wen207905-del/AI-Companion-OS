"""Background tick: absence emotion, relationship drift, optional proactive messages."""

from __future__ import annotations

import asyncio
import logging
import random
import uuid

from api.ws_hub import hub
from app_state import state
from config import USER_NAME
from engine.absence import hours_since_last_user_message
from engine.world_clock import now as world_now
from llm import router as llm_router

logger = logging.getLogger(__name__)

TICK_SECONDS = 300
PROACTIVE_MIN_HOURS = 2.0
PROACTIVE_LOVE_MIN = 70.0
PROACTIVE_CHANCE = 0.12


class LifeScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._last_proactive: dict[str, float] = {}

    def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _loop(self) -> None:
        await asyncio.sleep(15)
        while True:
            try:
                await self.tick()
            except Exception:
                logger.exception("LifeScheduler tick failed")
            await asyncio.sleep(TICK_SECONDS)

    async def tick(self) -> None:
        if not state.db or not state.emo_engine or not state.rel_engine:
            return
        if not state.persona_loader:
            return

        for character_id in state.persona_loader.personas:
            hours = hours_since_last_user_message(state.db, character_id)
            rel = state.rel_engine.get_summary(character_id)
            love = float(rel.get("love") or 0)

            state.emo_engine.apply_user_absence(character_id, hours, love=love)

            if love >= 50 and hours >= 6:
                state.rel_engine.apply_effect(
                    character_id, "security", -min(3.0, hours * 0.15), "absence_tick"
                )
                state.rel_engine.save_snapshot(character_id, "absence_tick")

            state.emo_engine.save_snapshot(character_id, "absence_tick")

            await self._maybe_proactive_message(character_id, hours, love, rel)

    async def _maybe_proactive_message(
        self, character_id: str, hours: float, love: float, rel: dict
    ) -> None:
        if hours < PROACTIVE_MIN_HOURS or love < PROACTIVE_LOVE_MIN:
            return
        last = self._last_proactive.get(character_id, 0)
        if world_now() - last < 3600:
            return
        if random.random() > PROACTIVE_CHANCE:
            return

        persona = state.persona_loader.get(character_id)
        if not persona:
            return
        name = persona.get("name", character_id)
        emo = state.emo_engine.get_summary(character_id)
        mood = emo.get("primary_mood", "平静")
        lonely = float(emo.get("lonely") or 0)

        system = (
            f"你是{name}。正在给{USER_NAME}发一条简短的私聊消息。"
            f"你们已经约{hours:.0f}小时没聊了。当前心情{mood}，孤独感{lonely:.0f}。"
            f"好感{love:.0f}，关系阶段{rel.get('stage_name', '')}。"
            "用1-2句口语化微信风格，表达想念或关心，不要加角色名前缀，不要像AI。"
        )
        if lonely >= 55:
            system += "语气可以软一点、带一点委屈或想念。"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"（{USER_NAME}很久没回消息了，你想主动发一句）"},
        ]
        try:
            reply = await llm_router.chat_completion(messages, channel="aux", max_tokens=120)
        except Exception:
            logger.exception("Proactive LLM failed for %s", character_id)
            return

        content = (reply or "").strip()
        if not content or len(content) < 2:
            return

        msg_id = f"pro_{uuid.uuid4().hex[:12]}"
        ts = world_now()
        state.db.execute(
            """INSERT INTO private_messages
               (id, character_id, sender_type, content, timestamp)
               VALUES (?, ?, ?, ?, ?)""",
            (msg_id, character_id, "character", content, ts),
        )
        state.db.commit()

        if state.memory_manager:
            state.memory_manager.store(
                character_id,
                content,
                role="character",
                scope="private",
                event_id=msg_id,
                intensity=65.0,
                memory_type="proactive",
            )

        self._last_proactive[character_id] = ts
        room = f"private:{character_id}"
        await hub.send_room(room, {
            "type": "message",
            "id": msg_id,
            "content": content,
            "sender_type": "character",
            "sender_id": character_id,
            "character_name": name,
            "timestamp": ts,
            "proactive": True,
        })
        logger.info("Proactive message sent: %s", character_id)


_scheduler: LifeScheduler | None = None


def get_scheduler() -> LifeScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = LifeScheduler()
    return _scheduler
