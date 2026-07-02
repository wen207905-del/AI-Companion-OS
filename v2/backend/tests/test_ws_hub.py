"""Tests for WebSocket hub."""

import asyncio
from unittest.mock import AsyncMock

from api.ws_hub import WsHub


def test_hub_broadcasts_to_all_room_members():
    async def _run():
        hub = WsHub()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        room = "private:test"

        hub.join(ws1, room)
        hub.join(ws2, room)

        await hub.send_room(room, {"type": "typing", "character_id": "test"})

        ws1.send_json.assert_awaited_once()
        ws2.send_json.assert_awaited_once()

    asyncio.run(_run())


def test_hub_leave_all_removes_client():
    async def _run():
        hub = WsHub()
        ws = AsyncMock()
        room = "private:test"
        hub.join(ws, room)
        hub.leave_all(ws)
        await hub.send_room(room, {"type": "ping"})
        ws.send_json.assert_not_awaited()

    asyncio.run(_run())
