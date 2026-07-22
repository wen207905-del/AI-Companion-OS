"""Tests for V4.1 / V4.2 mode router."""

from services.mode_router import is_scene_input, resolve_mode


def test_is_scene_input_multi_participant_alone_not_scene():
    """V4.2: mentioning multiple characters alone must not force long scene mode."""
    assert is_scene_input("你好", participant_count=2) is False
    assert is_scene_input("@白柔 @王大海 你们好", participant_count=2) is False


def test_is_scene_input_scene_markers():
    assert is_scene_input("我推开门走进客厅，看见叶如雪和柳青柠都在") is True


def test_is_scene_input_plain_chat():
    assert is_scene_input("在吗") is False
    assert is_scene_input("今天天气不错") is False


def test_resolve_mode_explicit():
    assert resolve_mode("随便说点什么", explicit_mode="scene") == "scene"
    assert resolve_mode("我推开门看见他们都在", explicit_mode="chat") == "chat"


def test_resolve_mode_auto_scene():
    assert resolve_mode(
        "我推开门，看见叶如雪和柳青柠在客厅里。",
        explicit_mode=None,
        participant_count=2,
    ) == "scene"


def test_resolve_mode_default_chat():
    assert resolve_mode("在吗", default="chat") == "chat"
    assert resolve_mode("白柔和王大海在吗", participant_count=2, default="chat") == "chat"
