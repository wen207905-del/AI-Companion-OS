"""Broadcast group list changes to all connected clients (global WS room)."""

from __future__ import annotations

from typing import Any

from api.ws_hub import hub


def group_list_item(group: dict[str, Any]) -> dict[str, Any]:
    members = group.get("members") or []
    return {
        "id": group["id"],
        "name": group.get("name", "新群聊"),
        "type": group.get("type", "custom"),
        "mode": group.get("mode", "free"),
        "created_at": group.get("created_at"),
        "member_count": len(members) if members else group.get("member_count", 0),
    }


async def broadcast_group_created(group: dict[str, Any]) -> None:
    await hub.send_room("global", {
        "type": "group_created",
        "group": group_list_item(group),
    })


async def broadcast_group_deleted(group_id: str) -> None:
    await hub.send_room("global", {
        "type": "group_deleted",
        "group_id": group_id,
    })
