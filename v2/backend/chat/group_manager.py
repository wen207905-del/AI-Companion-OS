"""Group chat manager — multi-character conversation orchestration."""

import logging
from typing import Any

logger = logging.getLogger("companion.group_manager")


class Group:
    def __init__(self, group_id: str, members: list[str] | None = None) -> None:
        self.group_id = group_id
        self.members: list[str] = members or []
        self.name: str = group_id


class GroupManager:
    """Manages group chat sessions with multiple characters."""

    def __init__(self) -> None:
        self._groups: dict[str, Group] = {}

    async def get_or_create(self, group_id: str) -> Group:
        if group_id not in self._groups:
            self._groups[group_id] = Group(group_id)
        return self._groups[group_id]

    async def add_member(self, group_id: str, character_id: str) -> None:
        group = await self.get_or_create(group_id)
        if character_id not in group.members:
            group.members.append(character_id)

    async def remove_member(self, group_id: str, character_id: str) -> None:
        group = await self.get_or_create(group_id)
        if character_id in group.members:
            group.members.remove(character_id)

    async def list_groups(self) -> list[dict[str, Any]]:
        return [
            {"group_id": g.group_id, "name": g.name, "member_count": len(g.members)}
            for g in self._groups.values()
        ]
