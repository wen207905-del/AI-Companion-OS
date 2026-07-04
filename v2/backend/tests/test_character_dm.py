"""Tests for V4.1 character DM frequency limits and selection."""

import sqlite3
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import init_db
from services.character_dm_service import (
    DmCandidate,
    MAX_ACTIVE_CONVERSATIONS,
    MAX_INITIATIONS_PER_DAY,
    can_initiate,
    can_open_new_conversation,
    count_active_conversations,
    count_initiations_today,
    evaluate_candidates,
    save_conversation,
    select_candidate,
)
from services.character_relation_service import seed_from_personas
from personality.persona_loader import PersonaLoader
from config import PERSONA_DIR


def _memory_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def _insert_conv(db, conv_id, a, b, initiator, *, status="active", age_hours=0):
    now = time.time() - age_hours * 3600
    ca, cb = (a, b) if a <= b else (b, a)
    db.execute(
        """
        INSERT INTO character_dm_conversation
        (id, character_a, character_b, initiator_id, trigger_type, trigger_reason,
         status, created_at, updated_at, last_message_at)
        VALUES (?, ?, ?, ?, 'daily_chat', 'test', ?, ?, ?, ?)
        """,
        (conv_id, ca, cb, initiator, status, now, now, now),
    )
    db.commit()


def test_daily_initiation_limit(memory_db):
    for i in range(MAX_INITIATIONS_PER_DAY):
        _insert_conv(memory_db, f"c{i}", "liu_qingning", "ye_ruxue", "liu_qingning", age_hours=i)
    assert count_initiations_today(memory_db, "liu_qingning") == MAX_INITIATIONS_PER_DAY
    assert can_initiate(memory_db, "liu_qingning") is False


def test_active_conversation_limit(memory_db):
    pairs = [
        ("cdm1", "a", "b", "a"),
        ("cdm2", "c", "d", "c"),
        ("cdm3", "e", "f", "e"),
    ]
    for cid, a, b, initiator in pairs:
        _insert_conv(memory_db, cid, a, b, initiator)
    assert count_active_conversations(memory_db) == MAX_ACTIVE_CONVERSATIONS
    assert can_open_new_conversation(memory_db) is False


def test_jealousy_trigger_priority(monkeypatch):
    db = _memory_db()
    loader = PersonaLoader(PERSONA_DIR)
    seed_from_personas(db, loader, force=True)

    from app_state import state
    state.db = db
    state.persona_loader = loader
    state.rel_engine = MagicMock()
    state.emo_engine = MagicMock()

    state.rel_engine.get_summary.side_effect = lambda cid: {
        "liu_qingning": {"jealousy": 72},
        "ye_ruxue": {"jealousy": 20},
        "bai_rou": {"jealousy": 15},
    }.get(cid, {"jealousy": 10})
    state.emo_engine.get_summary.side_effect = lambda cid: {
        "liu_qingning": {"jealous": 50},
    }.get(cid, {"jealous": 5})

    candidates = evaluate_candidates(db)
    assert candidates
    top = candidates[0]
    assert top.initiator_id == "liu_qingning"
    assert top.trigger_type == "jealousy_conflict"


def test_select_respects_limits(memory_db):
    for i in range(MAX_INITIATIONS_PER_DAY):
        _insert_conv(memory_db, f"x{i}", "liu_qingning", "ye_ruxue", "liu_qingning")
    candidates = [
        DmCandidate("liu_qingning", "ye_ruxue", "jealousy_conflict", 120, "test"),
        DmCandidate("bai_rou", "ye_ruxue", "daily_chat", 80, "test"),
    ]
    picked = select_candidate(memory_db, candidates)
    assert picked is not None
    assert picked.initiator_id == "bai_rou"


def test_save_conversation_persists_messages(memory_db):
    from app_state import state
    state.db = memory_db
    state.persona_loader = MagicMock()
    state.persona_loader.get_display_name.side_effect = lambda x: x

    candidate = DmCandidate(
        "liu_qingning", "ye_ruxue", "jealousy_conflict", 100, "test",
    )
    conv = save_conversation(candidate, [
        {"speaker_id": "liu_qingning", "content": "你刚才那句话是什么意思？"},
        {"speaker_id": "ye_ruxue", "content": "至少比你想象的了解。"},
    ])
    rows = memory_db.execute(
        "SELECT COUNT(*) AS cnt FROM character_dm_messages WHERE conversation_id = ?",
        (conv["id"],),
    ).fetchone()
    assert int(rows["cnt"]) == 2
