import sqlite3

import pytest

from config import init_db
from games.fate_dice import GameError, apply_action, create_session, get_current_session


class PersonaStub:
    names = {"a": "白柔", "b": "夜如雪"}

    def get(self, character_id):
        return {"id": character_id, "name": self.names[character_id]} if character_id in self.names else {}

    def get_display_name(self, character_id):
        return self.names[character_id]


@pytest.fixture
def game_db():
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    init_db(db)
    db.execute(
        "INSERT INTO group_chats (id, name, created_at) VALUES ('g1', '测试群', 1)"
    )
    db.executemany(
        "INSERT INTO group_chat_members (chat_id, character_id, joined_at) VALUES ('g1', ?, ?)",
        [("a", 1), ("b", 2)],
    )
    db.commit()
    return db


def test_create_session_has_user_and_group_members(game_db):
    session = create_session(game_db, "g1", PersonaStub(), total_rounds=2)
    assert session["status"] == "running"
    assert session["current_turn"]["participant_ref_id"] == "user"
    assert [p["participant_ref_id"] for p in session["participants"]] == ["user", "a", "b"]
    assert get_current_session(game_db, "g1")["id"] == session["id"]


def test_only_one_running_session_per_group(game_db):
    create_session(game_db, "g1", PersonaStub())
    with pytest.raises(GameError) as exc:
        create_session(game_db, "g1", PersonaStub())
    assert exc.value.code == "active_session_exists"


def test_turn_order_idempotency_round_and_final_settlement(game_db):
    session = create_session(game_db, "g1", PersonaStub(), total_rounds=1)
    with pytest.raises(GameError) as exc:
        apply_action(
            game_db, session["id"], action_type="roll", actor_ref_id="a",
            idempotency_key="wrong-turn", randint_fn=lambda _a, _b: 50,
        )
    assert exc.value.code == "not_your_turn"

    first = apply_action(
        game_db, session["id"], action_type="roll", actor_ref_id="user",
        expected_version=1, idempotency_key="roll-user", randint_fn=lambda _a, _b: 80,
    )
    replay = apply_action(
        game_db, session["id"], action_type="roll", actor_ref_id="user",
        expected_version=1, idempotency_key="roll-user", randint_fn=lambda _a, _b: 1,
    )
    assert replay["idempotent_replay"] is True
    assert replay["round_rolls"] == first["round_rolls"]

    second = apply_action(
        game_db, session["id"], action_type="roll", actor_ref_id="a",
        idempotency_key="roll-a", randint_fn=lambda _a, _b: 120,
    )
    final = apply_action(
        game_db, session["id"], action_type="roll", actor_ref_id="b",
        expected_version=second["state_version"], idempotency_key="roll-b",
        randint_fn=lambda _a, _b: 30,
    )
    assert final["status"] == "finished"
    assert final["winners"] == ["a"]
    assert next(p for p in final["participants"] if p["participant_ref_id"] == "a")["score"] == 1
    assert len(final["round_history"]) == 1


def test_version_conflict_and_manual_end(game_db):
    session = create_session(game_db, "g1", PersonaStub())
    with pytest.raises(GameError) as exc:
        apply_action(
            game_db, session["id"], action_type="roll", expected_version=99,
            idempotency_key="stale",
        )
    assert exc.value.code == "version_conflict"
    ended = apply_action(
        game_db, session["id"], action_type="end", actor_ref_id="user",
        idempotency_key="end",
    )
    assert ended["status"] == "cancelled"
    assert get_current_session(game_db, "g1") is None
