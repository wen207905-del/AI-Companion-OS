"""Memory manager tests."""

from memory.memory_manager import MemoryManager, format_memories_block


def test_store_and_recall(memory_db):
    mm = MemoryManager(memory_db)
    mm.store("bai_rou", "今天做了红烧肉", role="user", scope="private")
    mm.store("bai_rou", "嗯，好吃", role="character", scope="private")
    results = mm.recall("bai_rou", "红烧肉", limit=3, scope="private")
    assert any("红烧肉" in r for r in results)


def test_format_memories_block():
    text = format_memories_block(["用户：你好", "我：在呢"])
    assert "相关记忆" in text
    assert "你好" in text
