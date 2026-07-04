"""V3 database schema tests."""

import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from v3.db import V3Database


@pytest.fixture
def memory_db():
    db = V3Database(":memory:")
    db.connect()
    db.create_tables()
    db._create_v4_tables()
    yield db
    db.close()


def test_create_tables(memory_db):
    row = memory_db.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='world_state'",
    ).fetchone()
    assert row is not None


def test_tick_counter_increments(memory_db):
    first = memory_db.get_tick_id()
    second = memory_db.get_tick_id()
    assert second == first + 1


def test_character_upsert(memory_db):
    memory_db.upsert_character_state("ye_ruxue", "reading", "home")
    chars = memory_db.get_all_characters()
    assert any(c["character_id"] == "ye_ruxue" for c in chars)


def test_memory_item_roundtrip(memory_db):
    item_id = memory_db.insert_memory_item(
        "ye_ruxue",
        content="测试记忆",
        memory_type="short",
        importance=0.8,
    )
    assert item_id > 0
    items = memory_db.get_memories_by_character("ye_ruxue", limit=5)
    assert items[0]["content"] == "测试记忆"
