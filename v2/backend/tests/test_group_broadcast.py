"""Tests for group list WebSocket broadcasts."""

import asyncio
from unittest.mock import AsyncMock, patch

from chat.group_broadcast import broadcast_group_created, broadcast_group_deleted, group_list_item


def test_group_list_item_from_members():
    item = group_list_item({
        "id": "grp_abc",
        "name": "测试",
        "type": "custom",
        "mode": "free",
        "created_at": 1.0,
        "members": ["a", "b"],
    })
    assert item["member_count"] == 2
    assert item["id"] == "grp_abc"


def test_broadcast_group_created_sends_global():
    async def _run():
        with patch("chat.group_broadcast.hub") as hub:
            hub.send_room = AsyncMock()
            group = {
                "id": "grp_x",
                "name": "新群",
                "members": ["bai_rou"],
                "created_at": 99.0,
            }
            await broadcast_group_created(group)
            hub.send_room.assert_awaited_once()
            args = hub.send_room.await_args
            assert args[0][0] == "global"
            assert args[0][1]["type"] == "group_created"
            assert args[0][1]["group"]["id"] == "grp_x"

    asyncio.run(_run())


def test_broadcast_group_deleted_sends_global():
    async def _run():
        with patch("chat.group_broadcast.hub") as hub:
            hub.send_room = AsyncMock()
            await broadcast_group_deleted("grp_y")
            hub.send_room.assert_awaited_once_with(
                "global",
                {"type": "group_deleted", "group_id": "grp_y"},
            )

    asyncio.run(_run())
