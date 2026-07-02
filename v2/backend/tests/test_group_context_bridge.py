"""Private-to-group context bridge tests."""

import time

from chat.context_builder import memory_block_for_group
from chat.history_loader import load_recent_private_bridge
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


def test_memory_block_for_group_merges_private(memory_db):
    from app_state import state
    from personality.persona_loader import PersonaLoader
    from config import PERSONA_DIR

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
    assert "私聊延续" in block
    assert "明天去西湖" in block
    assert "相关记忆" in block
