"""Private-to-group context bridge tests."""

import time

from chat.context_builder import memory_block_for_group
from chat.history_loader import (
    load_recent_private_bridge,
    load_recent_private_continuity_hint,
)
from memory.memory_manager import MemoryManager


def test_private_bridge_includes_recent_messages(memory_db):
    ts = time.time()
    memory_db.execute(
        """
        INSERT INTO private_messages (id, character_id, sender_type, content, timestamp)
        VALUES ('m1', 'bai_rou', 'user', '今晚吃什么', ?),
               ('m2', 'bai_rou', 'character', '做了你喜欢的红烧肉', ?)
        """,
        (ts, ts + 1),
    )
    memory_db.commit()

    block = load_recent_private_bridge(memory_db, "bai_rou", "白柔")
    assert "私聊延续" in block
    assert "今晚吃什么" in block
    assert "红烧肉" in block


def test_private_bridge_skips_stale_messages(memory_db):
    old_ts = time.time() - 86400
    memory_db.execute(
        """
        INSERT INTO private_messages (id, character_id, sender_type, content, timestamp)
        VALUES ('m1', 'bai_rou', 'user', '旧话题', ?)
        """,
        (old_ts,),
    )
    memory_db.commit()

    block = load_recent_private_bridge(memory_db, "bai_rou", "白柔")
    assert block == ""


def test_private_continuity_contains_no_private_content(memory_db):
    ts = time.time()
    memory_db.execute(
        """
        INSERT INTO private_messages (id, character_id, sender_type, content, timestamp)
        VALUES ('m1', 'bai_rou', 'user', '这是绝对不能在群里说的秘密', ?)
        """,
        (ts,),
    )
    memory_db.commit()

    hint = load_recent_private_continuity_hint(memory_db, "bai_rou")
    assert "私聊连续性" in hint
    assert "当前关系与情绪" in hint
    assert "绝对不能在群里说的秘密" not in hint


def test_memory_block_for_group_excludes_private_by_default(memory_db, monkeypatch):
    import chat.context_builder as cb
    from app_state import state
    from personality.persona_loader import PersonaLoader
    from config import PERSONA_DIR

    monkeypatch.setattr(cb, "GROUP_PRIVATE_BRIDGE_ENABLED", False)
    monkeypatch.setattr(cb, "GROUP_PRIVATE_CONTINUITY_ENABLED", True)

    state.db = memory_db
    state.memory_manager = MemoryManager(memory_db)
    state.persona_loader = PersonaLoader(PERSONA_DIR)

    ts = time.time()
    memory_db.execute(
        """
        INSERT INTO private_messages (id, character_id, sender_type, content, timestamp)
        VALUES ('m1', 'bai_rou', 'user', '明天去西湖', ?)
        """,
        (ts,),
    )
    memory_db.commit()

    state.memory_manager.store(
        "bai_rou", "私聊里约了散步", role="user", scope="private",
    )
    state.memory_manager.store(
        "bai_rou", "群里也提到过", role="user", scope="group", scope_id="grp1",
    )

    block = memory_block_for_group("bai_rou", "西湖", "grp1")
    assert "私聊延续" not in block
    assert "私聊连续性" in block
    assert "明天去西湖" not in block
    assert "私聊里约了散步" not in block
    assert "群里也提到过" in block


def test_memory_block_for_group_bridge_when_enabled(memory_db, monkeypatch):
    import chat.context_builder as cb
    from app_state import state
    from personality.persona_loader import PersonaLoader
    from config import PERSONA_DIR

    monkeypatch.setattr(cb, "GROUP_PRIVATE_BRIDGE_ENABLED", True)

    state.db = memory_db
    state.memory_manager = MemoryManager(memory_db)
    state.persona_loader = PersonaLoader(PERSONA_DIR)

    ts = time.time()
    memory_db.execute(
        """
        INSERT INTO private_messages (id, character_id, sender_type, content, timestamp)
        VALUES ('m1', 'bai_rou', 'user', '明天去西湖', ?)
        """,
        (ts,),
    )
    memory_db.commit()

    block = memory_block_for_group("bai_rou", "西湖", "grp1")
    assert "私聊延续" in block
    assert "明天去西湖" in block


def test_group_to_private_to_group_keeps_continuity_without_leak(memory_db, monkeypatch):
    import chat.context_builder as cb
    from app_state import state
    from chat.group_memory import record_group_user_message

    monkeypatch.setattr(cb, "GROUP_PRIVATE_BRIDGE_ENABLED", False)
    monkeypatch.setattr(cb, "GROUP_PRIVATE_CONTINUITY_ENABLED", True)
    state.db = memory_db
    state.memory_manager = MemoryManager(memory_db)
    state.persona_loader = None

    record_group_user_message(
        ["bai_rou", "wang_dahai"],
        group_id="grp1",
        group_name="朋友群",
        content="周末一起看电影",
        event_id="group_evt_1",
    )
    private_block = cb.memory_block_for(
        "bai_rou", "周末电影", scope="private",
    )
    assert "[群聊·朋友群]" in private_block
    assert "周末一起看电影" in private_block

    ts = time.time()
    memory_db.execute(
        """
        INSERT INTO private_messages (id, character_id, sender_type, content, timestamp)
        VALUES ('private_1', 'bai_rou', 'user', '私下告诉你我的秘密暗号是蓝鲸', ?)
        """,
        (ts,),
    )
    memory_db.commit()
    state.memory_manager.store(
        "bai_rou",
        "私下告诉你我的秘密暗号是蓝鲸",
        role="user",
        scope="private",
        event_id="private_1",
    )

    group_block = cb.memory_block_for_group(
        "bai_rou", "回来继续聊", "grp1",
    )
    assert "私聊连续性" in group_block
    assert "周末一起看电影" in group_block
    assert "蓝鲸" not in group_block
