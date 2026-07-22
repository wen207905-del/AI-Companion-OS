"""REST API integration tests."""

import pytest

from config import APP_VERSION


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ok", "degraded")
    assert data["version"] == APP_VERSION
    assert "llm" in data
    assert "llm_stream" in data
    assert data["user"]["name"] == "许汉文"
    assert "checks" in data
    assert data["checks"]["database"]["ok"] is True
    assert "group_flags" in data


def test_health_root_alias(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert "checks" in data
    assert data["checks"]["database"]["ok"] is True


def test_user_profile(client):
    res = client.get("/api/user")
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "许汉文"
    assert data["nickname"] == "汉文"


def test_list_characters(client):
    res = client.get("/api/characters")
    assert res.status_code == 200
    chars = res.json()["characters"]
    assert len(chars) >= 12
    assert all(c.get("id") and c.get("name") for c in chars)


def test_get_character(client):
    res = client.get("/api/character/bai_rou")
    assert res.status_code == 200
    data = res.json()
    assert data["persona"]["name"] == "白柔"
    assert "relationship" in data
    assert "growth" in data
    assert "body_experiences" in data


def test_character_not_found(client):
    res = client.get("/api/character/nonexistent_xyz")
    assert res.status_code == 404


def test_list_groups(client):
    res = client.get("/api/groups")
    assert res.status_code == 200
    assert isinstance(res.json()["groups"], list)


def test_create_and_get_group(client):
    res = client.post(
        "/api/groups",
        json={"name": "闺蜜局", "member_ids": ["bai_rou", "liu_qingning", "hua_li"]},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "闺蜜局"
    assert len(data["members"]) == 3

    res2 = client.get(f"/api/group/{data['id']}")
    assert res2.status_code == 200
    assert set(res2.json()["members"]) == {"bai_rou", "liu_qingning", "hua_li"}


def test_dashboard(client):
    res = client.get("/api/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert data["total_characters"] >= 12
    assert "level" in data["characters"][0]


def test_create_group_requires_members(client):
    res = client.post("/api/groups", json={"name": "空群", "member_ids": []})
    assert res.status_code == 400


def test_create_group(client):
    res = client.post(
        "/api/groups",
        json={"name": "测试群", "member_ids": ["bai_rou", "liu_qingning"]},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "测试群"
    assert "bai_rou" in data["members"]


def test_llm_providers(client):
    res = client.get("/api/llm/providers")
    assert res.status_code == 200
    providers = res.json()["providers"]
    ids = {p["id"] for p in providers}
    assert "deepseek" in ids
    assert "ollama" not in ids


def test_private_message_edit_and_delete(client):
    import time

    from app_state import state
    from chat.message_service import ensure_message_schema

    ensure_message_schema(state.db)
    msg_id = "test_msg_edit_1"
    state.db.execute(
        """
        INSERT INTO private_messages (id, character_id, sender_type, content, timestamp)
        VALUES (?, 'bai_rou', 'user', '原始消息', ?)
        """,
        (msg_id, time.time()),
    )
    state.db.commit()

    res = client.patch(
        f"/api/chat/bai_rou/messages/{msg_id}",
        json={"content": "修改后的消息"},
    )
    assert res.status_code == 200
    assert res.json()["content"] == "修改后的消息"
    assert res.json()["edited"] is True

    res2 = client.delete(f"/api/chat/bai_rou/messages/{msg_id}")
    assert res2.status_code == 200
    assert res2.json()["ok"] is True
