"""Tests for scoped style reference loader."""

from chat import style_reference_loader as srl


def test_private_guide_non_empty(monkeypatch):
    monkeypatch.setattr(srl, "STYLE_REFERENCE_ENABLED", True)
    srl.clear_style_cache()
    text = srl.load_style_guides("private")
    assert len(text) > 500
    assert "私聊" in text or "CG" in text or "互动小说" in text


def test_group_guide_non_empty_and_shorter_scope(monkeypatch):
    monkeypatch.setattr(srl, "STYLE_REFERENCE_ENABLED", True)
    srl.clear_style_cache()
    group = srl.load_style_guides("group")
    assert len(group) > 200
    assert "群聊" in group
    assert "微信" in group or "连发" in group
    assert "骰子" in group or "游戏" in group


def test_style_reference_block_substitutes_user_name(monkeypatch):
    monkeypatch.setattr(srl, "STYLE_REFERENCE_ENABLED", True)
    srl.clear_style_cache()
    block = srl.style_reference_block("private")
    assert "{USER_NAME}" not in block


def test_group_and_private_blocks_differ(monkeypatch):
    monkeypatch.setattr(srl, "STYLE_REFERENCE_ENABLED", True)
    srl.clear_style_cache()
    priv = srl.style_reference_block("private")
    grp = srl.style_reference_block("group")
    assert priv != grp
    assert "群聊" in grp


def test_style_guides_empty_when_disabled(monkeypatch):
    monkeypatch.setattr(srl, "STYLE_REFERENCE_ENABLED", False)
    srl.clear_style_cache()
    assert srl.load_style_guides("private") == ""
    assert srl.style_reference_block("group") == ""
