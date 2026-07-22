import uuid


def test_game_catalog_exposes_real_fate_dice(client):
    response = client.get("/api/v4/game-catalog")
    assert response.status_code == 200
    game = response.json()["games"][0]
    assert game["id"] == "fate_dice"
    assert game["status"] == "available"


def test_fate_dice_api_full_one_round_flow(client):
    group_response = client.post(
        "/api/groups",
        json={
            "name": f"骰子接口测试-{uuid.uuid4().hex[:6]}",
            "member_ids": ["bai_rou", "ye_ruxue"],
        },
    )
    assert group_response.status_code == 200
    group_id = group_response.json()["id"]

    try:
        created = client.post(
            f"/api/v4/groups/{group_id}/game-sessions",
            json={"game_type": "fate_dice", "settings": {"total_rounds": 1}},
        )
        assert created.status_code == 200
        session = created.json()
        assert session["settings"]["total_rounds"] == 1

        current = client.get(
            f"/api/v4/groups/{group_id}/game-sessions/current"
        ).json()["session"]
        assert current["id"] == session["id"]

        while session["status"] == "running":
            actor = session["current_turn"]["participant_ref_id"]
            action = client.post(
                f"/api/v4/game-sessions/{session['id']}/actions",
                json={
                    "action_type": "roll",
                    "actor_ref_id": actor,
                    "expected_version": session["state_version"],
                    "idempotency_key": f"roll-{actor}-{session['state_version']}",
                },
            )
            assert action.status_code == 200
            session = action.json()

        assert session["status"] == "finished"
        assert session["winners"]
        assert len(session["round_history"]) == 1

        events = client.get(
            f"/api/v4/game-sessions/{session['id']}/events"
        )
        assert events.status_code == 200
        assert len(events.json()["events"]) == 4
    finally:
        deleted = client.delete(f"/api/group/{group_id}")
        assert deleted.status_code == 200


def test_game_action_requires_idempotency_key(client):
    group = client.post(
        "/api/groups",
        json={"name": "缺少幂等键测试", "member_ids": ["bai_rou"]},
    ).json()
    try:
        session = client.post(
            f"/api/v4/groups/{group['id']}/game-sessions",
            json={"game_type": "fate_dice"},
        ).json()
        response = client.post(
            f"/api/v4/game-sessions/{session['id']}/actions",
            json={"action_type": "roll"},
        )
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "idempotency_key_required"
    finally:
        client.delete(f"/api/group/{group['id']}")
