"""Tests for group history loading."""

import time

from chat.history_loader import load_group_history, load_group_history_for_character


class _FakeLoader:
    def get_display_name(self, char_id: str) -> str:
        names = {"bai_rou": "白柔", "liu_qingning": "柳青柠"}
        return names.get(char_id, char_id)


def test_load_group_history_formats_character_names(memory_db):
    ts = time.time()
    memory_db.execute(
        """INSERT INTO group_messages
           (id, chat_id, sender_type, sender_id, content, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("m1", "default", "user", "user", "大家好", ts),
    )
    memory_db.execute(
        """INSERT INTO group_messages
           (id, chat_id, sender_type, sender_id, content, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("m2", "default", "character", "bai_rou", "嗯，在呢", ts + 1),
    )
    memory_db.commit()

    history = load_group_history(memory_db, "default", _FakeLoader(), limit=10)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert "大家好" in history[0]["content"]
    assert "许汉文" in history[0]["content"]
    assert history[1]["role"] == "assistant"
    assert "白柔" in history[1]["content"]


def test_load_group_history_redacts_intimate_for_non_witness(memory_db):
    ts = time.time()
    intimate = "*搂着老婆* 轻轻弄她"
    memory_db.execute(
        """INSERT INTO group_messages
           (id, chat_id, sender_type, sender_id, content, timestamp)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("m1", "default", "user", "user", intimate, ts),
    )
    memory_db.commit()

    members = ["bai_rou", "wang_dahai"]
    loader = _FakeLoader()
    bai_hist = load_group_history_for_character(
        memory_db, "default", loader, "bai_rou", members, limit=10,
    )
    dahai_hist = load_group_history_for_character(
        memory_db, "default", loader, "wang_dahai", members, limit=10,
    )
    assert "弄她" in bai_hist[0]["content"]
    assert "不在现场" in dahai_hist[0]["content"]
    assert "弄她" not in dahai_hist[0]["content"]
