"""Group user identity and scene visibility tests."""

from chat.group_context import (
    character_witnessed_scene,
    group_user_identity_block,
    group_user_scene_directive,
    visible_user_message_for_character,
)


class _FakeLoader:
    personas = {"bai_rou": {}, "wang_dahai": {}}

    def get_display_name(self, cid: str) -> str:
        return {"bai_rou": "白柔", "wang_dahai": "王大海"}.get(cid, cid)


def test_identity_block_names_user_and_wife():
    block = group_user_identity_block()
    assert "许汉文" in block
    assert "汉文" in block
    assert "白柔" in block
    assert "老婆" in block


def test_wife_witnesses_intimate_scene():
    msg = "*搂着老婆* 轻轻弄她"
    members = ["bai_rou", "wang_dahai"]
    loader = _FakeLoader()
    assert character_witnessed_scene(msg, "bai_rou", members, loader)
    assert not character_witnessed_scene(msg, "wang_dahai", members, loader)


def test_non_witness_gets_redacted_message():
    msg = "*搂着老婆* 轻轻弄她"
    members = ["bai_rou", "wang_dahai"]
    loader = _FakeLoader()
    visible = visible_user_message_for_character(msg, "wang_dahai", members, loader)
    assert "弄她" not in visible
    assert "不在现场" in visible
    assert visible_user_message_for_character(msg, "bai_rou", members, loader) == msg


def test_scene_directive_witness_vs_non_witness():
    msg = "*搂着老婆白柔* 轻轻弄她"
    loader = _FakeLoader()
    members = ["bai_rou", "wang_dahai"]

    wife_block = group_user_scene_directive(msg, "bai_rou", members, loader)
    assert "在场" in wife_block or "亲历" in wife_block
    assert "弄她" in wife_block

    dahai_block = group_user_scene_directive(msg, "wang_dahai", members, loader)
    assert "不在现场" in dahai_block
    assert "禁止" in dahai_block
    assert "弄她" not in dahai_block
