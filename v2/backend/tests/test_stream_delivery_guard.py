"""Guarded group replies must be validated before broadcast."""

import asyncio
from unittest.mock import AsyncMock

import chat.stream_delivery as sd
from chat.group_reply_guard import GuardResult


def test_guarded_group_reply_is_buffered_before_broadcast(monkeypatch):
    events = []
    saved = []

    generate = AsyncMock(return_value=("白柔：短回复", {}, ""))
    send_room = AsyncMock(side_effect=lambda room, payload: events.append(payload))
    monkeypatch.setattr(sd, "generate_reply", generate)
    monkeypatch.setattr(sd.hub, "send_room", send_room)
    monkeypatch.setattr(sd, "LLM_STREAM", True)
    monkeypatch.setattr(sd.state, "memory_manager", None)

    async def _run():
        return await sd.deliver_character_reply(
            "group:test",
            reply_id="msg_1",
            llm_messages=[{"role": "user", "content": "你好"}],
            persona={"id": "bai_rou", "name": "白柔"},
            rel_summary={},
            llm_choice=None,
            ws_meta={"character_id": "bai_rou", "sender_id": "bai_rou"},
            save_to_db=lambda *args: saved.append(args),
            memory_scope="group",
            memory_scope_id="grp_test",
            present_members=["bai_rou"],
            content_filter=lambda text: GuardResult(True, "短回复"),
        )

    content = asyncio.run(_run())
    assert content == "短回复"
    assert len(saved) == 1
    assert [event["type"] for event in events] == ["message"]
    assert "on_delta" not in generate.call_args.kwargs


def test_blocked_group_reply_never_reaches_room(monkeypatch):
    events = []
    saved = []

    monkeypatch.setattr(
        sd,
        "generate_reply",
        AsyncMock(return_value=("王大海：冒名回复", {}, "")),
    )
    monkeypatch.setattr(
        sd.hub,
        "send_room",
        AsyncMock(side_effect=lambda room, payload: events.append(payload)),
    )
    monkeypatch.setattr(sd, "LLM_STREAM", True)
    monkeypatch.setattr(sd.state, "memory_manager", None)

    async def _run():
        return await sd.deliver_character_reply(
            "group:test",
            reply_id="msg_2",
            llm_messages=[{"role": "user", "content": "你好"}],
            persona={"id": "bai_rou", "name": "白柔"},
            rel_summary={},
            llm_choice=None,
            ws_meta={"character_id": "bai_rou", "sender_id": "bai_rou"},
            save_to_db=lambda *args: saved.append(args),
            memory_scope="group",
            memory_scope_id="grp_test",
            present_members=["bai_rou", "wang_dahai"],
            content_filter=lambda text: GuardResult(False, text, "speaker_mismatch"),
        )

    content = asyncio.run(_run())
    assert content == ""
    assert saved == []
    assert events == []
