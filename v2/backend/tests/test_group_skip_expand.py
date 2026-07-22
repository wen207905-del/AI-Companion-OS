"""P0 group expand/skip unit tests."""

import asyncio
from unittest.mock import AsyncMock, patch

import chat.reply_service as rs


def test_group_skip_expand_keeps_short_reply(monkeypatch):
    monkeypatch.setattr(rs, "GROUP_SKIP_EXPAND", True)
    monkeypatch.setattr(rs, "CONTENT_MODE", "unrestricted")
    monkeypatch.setattr(rs, "LLM_STREAM", False)
    monkeypatch.setattr(rs, "GROUP_MAX_REPLY_CHARS", 450)

    short = "「嗯」*点头* 好的。"
    expand = AsyncMock(return_value="x" * 900)

    async def _run():
        with patch.object(rs.llm_router, "chat_completion", AsyncMock(return_value=short)):
            with patch.object(rs, "_expand_short_reply", expand):
                with patch.object(rs, "is_choice_available", return_value=True):
                    return await rs.generate_reply(
                        [{"role": "user", "content": "hi"}],
                        {"id": "bai_rou", "name": "白柔"},
                        chat_mode="group",
                    )

    content, _, _ = asyncio.run(_run())
    assert content == short
    expand.assert_not_called()


def test_private_still_can_expand(monkeypatch):
    monkeypatch.setattr(rs, "GROUP_SKIP_EXPAND", True)
    monkeypatch.setattr(rs, "PRIVATE_SKIP_EXPAND", False)
    monkeypatch.setattr(rs, "CONTENT_MODE", "unrestricted")
    monkeypatch.setattr(rs, "LLM_STREAM", False)

    short = "嗯。"
    expanded = "扩写后的长回复。" * 40

    async def _run():
        with patch.object(rs.llm_router, "chat_completion", AsyncMock(return_value=short)):
            with patch.object(rs, "_expand_short_reply", AsyncMock(return_value=expanded)) as expand:
                with patch.object(rs, "is_choice_available", return_value=True):
                    content, action, thought = await rs.generate_reply(
                        [{"role": "user", "content": "hi"}],
                        {"id": "bai_rou", "name": "白柔"},
                        chat_mode="private",
                    )
                expand.assert_called_once()
                return content, action, thought

    content, _, _ = asyncio.run(_run())
    assert content == expanded


def test_private_skip_expand_by_default(monkeypatch):
    monkeypatch.setattr(rs, "PRIVATE_SKIP_EXPAND", True)
    monkeypatch.setattr(rs, "CONTENT_MODE", "unrestricted")
    monkeypatch.setattr(rs, "LLM_STREAM", False)

    short = "嗯。"
    expand = AsyncMock(return_value="x" * 900)

    async def _run():
        with patch.object(rs.llm_router, "chat_completion", AsyncMock(return_value=short)):
            with patch.object(rs, "_expand_short_reply", expand):
                with patch.object(rs, "is_choice_available", return_value=True):
                    return await rs.generate_reply(
                        [{"role": "user", "content": "hi"}],
                        {"id": "bai_rou", "name": "白柔"},
                        chat_mode="private",
                        structured_chat=False,
                    )

    content, _, _ = asyncio.run(_run())
    assert content == short
    expand.assert_not_called()


def test_truncate_group_reply_helper():
    text = "短句。" + ("内容" * 200)
    out = rs._truncate_group_reply(text, max_chars=50)
    assert len(out) <= 50
