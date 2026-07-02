"""Tests for message edit/delete."""

import pytest

from chat.message_service import (
    MessageError,
    delete_group_message,
    delete_private_message,
    edit_group_message,
    edit_private_message,
    ensure_message_schema,
)
from chat.regenerate_service import prepare_group_regenerate, prepare_private_regenerate


@pytest.fixture
def msg_db(memory_db):
    ensure_message_schema(memory_db)
    memory_db.execute(
        """
        INSERT INTO group_chats (id, name, created_at)
        VALUES ('grp_test', '测试群', 1.0)
        """
    )
    memory_db.commit()
    return memory_db


def test_edit_private_user_message(msg_db):
    msg_db.execute(
        """
        INSERT INTO private_messages
        (id, character_id, sender_type, content, timestamp)
        VALUES ('evt_1', 'bai_rou', 'user', '旧内容', 100.0)
        """
    )
    msg_db.execute(
        """
        INSERT INTO event_log
        (event_id, event_type, timestamp, participants, raw_input, analysis_result)
        VALUES ('evt_1', 'conversation', 100.0, '[]', '旧内容', '[]')
        """
    )
    msg_db.commit()

    result = edit_private_message(msg_db, "bai_rou", "evt_1", "新内容")
    assert result["content"] == "新内容"
    assert result["edited"] is True

    row = msg_db.execute(
        "SELECT content, edited FROM private_messages WHERE id = 'evt_1'"
    ).fetchone()
    assert row["content"] == "新内容"
    assert row["edited"] == 1


def test_cannot_edit_character_message(msg_db):
    msg_db.execute(
        """
        INSERT INTO private_messages
        (id, character_id, sender_type, content, timestamp)
        VALUES ('msg_c', 'bai_rou', 'character', '角色回复', 100.0)
        """
    )
    msg_db.commit()
    with pytest.raises(MessageError, match="只能编辑"):
        edit_private_message(msg_db, "bai_rou", "msg_c", "改不了")


def test_delete_private_message(msg_db):
    msg_db.execute(
        """
        INSERT INTO private_messages
        (id, character_id, sender_type, content, timestamp)
        VALUES ('evt_del', 'bai_rou', 'user', '待删', 100.0)
        """
    )
    msg_db.commit()
    assert delete_private_message(msg_db, "bai_rou", "evt_del") is True
    assert msg_db.execute(
        "SELECT id FROM private_messages WHERE id = 'evt_del'"
    ).fetchone() is None


def test_edit_group_user_message(msg_db):
    msg_db.execute(
        """
        INSERT INTO group_messages
        (id, chat_id, sender_type, sender_id, content, timestamp)
        VALUES ('gmsg_1', 'grp_test', 'user', 'user', '你好', 100.0)
        """
    )
    msg_db.commit()
    result = edit_group_message(msg_db, "grp_test", "gmsg_1", "你好呀")
    assert result["content"] == "你好呀"
    assert delete_group_message(msg_db, "grp_test", "gmsg_1") is True


def test_prepare_private_regenerate(msg_db):
    msg_db.execute(
        """
        INSERT INTO private_messages
        (id, character_id, sender_type, content, timestamp)
        VALUES ('evt_u', 'bai_rou', 'user', '你想我吗', 100.0)
        """
    )
    msg_db.execute(
        """
        INSERT INTO private_messages
        (id, character_id, sender_type, content, timestamp)
        VALUES ('msg_r', 'bai_rou', 'character', '旧回复', 101.0)
        """
    )
    msg_db.commit()

    user_text = prepare_private_regenerate(msg_db, "bai_rou", "msg_r")
    assert user_text == "你想我吗"
    assert msg_db.execute(
        "SELECT id FROM private_messages WHERE id = 'msg_r'"
    ).fetchone() is None


def test_prepare_private_regenerate_not_latest(msg_db):
    msg_db.execute(
        """
        INSERT INTO private_messages
        (id, character_id, sender_type, content, timestamp)
        VALUES ('msg_old', 'bai_rou', 'character', '旧', 100.0),
               ('msg_new', 'bai_rou', 'character', '新', 200.0)
        """
    )
    msg_db.commit()
    with pytest.raises(MessageError, match="最近一条"):
        prepare_private_regenerate(msg_db, "bai_rou", "msg_old")


def test_prepare_group_regenerate(msg_db):
    msg_db.execute(
        """
        INSERT INTO group_messages
        (id, chat_id, sender_type, sender_id, content, timestamp)
        VALUES ('gu', 'grp_test', 'user', 'user', '大家好', 100.0),
               ('gc', 'grp_test', 'character', 'bai_rou', '旧群回复', 101.0)
        """
    )
    msg_db.commit()
    char_id, user_text = prepare_group_regenerate(msg_db, "grp_test", "gc")
    assert char_id == "bai_rou"
    assert user_text == "大家好"
    assert msg_db.execute(
        "SELECT id FROM group_messages WHERE id = 'gc'"
    ).fetchone() is None
