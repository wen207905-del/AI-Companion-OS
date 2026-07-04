"""Background tick: absence emotion, relationship drift, emotion tick, proactive shares."""

from __future__ import annotations

import asyncio
import logging

from app_state import state
from engine.absence import hours_since_last_user_message
from services.emotion_tick import run_emotion_tick
from services.proactive_share_service import run_proactive_tick
from services.character_dm_service import run_character_dm_tick

logger = logging.getLogger(__name__)

TICK_SECONDS = 300


class LifeScheduler:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None

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

            if love >= 50 and hours >= 6:
                state.rel_engine.apply_effect(
                    character_id, "security", -min(3.0, hours * 0.15), "absence_tick"
                )
                state.rel_engine.save_snapshot(character_id, "absence_tick")

        await run_emotion_tick()
        await run_proactive_tick()
        await run_character_dm_tick()


_scheduler: LifeScheduler | None = None


def get_scheduler() -> LifeScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = LifeScheduler()
    return _scheduler
