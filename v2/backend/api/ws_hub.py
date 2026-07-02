"""Multi-client WebSocket room hub for cross-device sync."""

from __future__ import annotations

from collections import defaultdict

from fastapi import WebSocket


class WsHub:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._ws_rooms: dict[WebSocket, set[str]] = defaultdict(set)

    def join(self, websocket: WebSocket, room: str) -> None:
        self._rooms[room].add(websocket)
        self._ws_rooms[websocket].add(room)

    def leave_all(self, websocket: WebSocket) -> None:
        for room in list(self._ws_rooms.get(websocket, set())):
            self._rooms[room].discard(websocket)
            if not self._rooms[room]:
                del self._rooms[room]
        self._ws_rooms.pop(websocket, None)

    async def send_room(self, room: str, data: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._rooms.get(room, set())):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.leave_all(ws)

    async def send_rooms(self, rooms: list[str], data: dict) -> None:
        for room in rooms:
            await self.send_room(room, data)


hub = WsHub()
