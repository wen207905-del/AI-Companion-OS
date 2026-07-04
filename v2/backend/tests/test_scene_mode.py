"""Tests for V4.1 scene mode parsing."""

import json

from services.scene_mode_service import parse_scene_response, _validate_scene_payload


def test_parse_scene_response_valid_json():
    raw = json.dumps({
        "narration": "门被推开，客厅里两人同时看过来。",
        "participants": ["ye_ruxue", "liu_qingning"],
        "events": [
            {
                "character_id": "ye_ruxue",
                "action": "放下手中的书，目光平静",
                "dialogue": "你来了。",
                "emotion_delta": {"calm": 2},
            },
            {
                "character_id": "liu_qingning",
                "action": "别过脸",
                "dialogue": "哼，谁等你了。",
            },
        ],
    }, ensure_ascii=False)
    result = parse_scene_response(raw)
    assert result["narration"].startswith("门被推开")
    assert len(result["participants"]) == 2
    assert len(result["events"]) == 2
    assert result["events"][0]["character_id"] == "ye_ruxue"
    assert "parse_fallback" not in result or not result.get("parse_fallback")


def test_parse_scene_response_fallback():
    result = parse_scene_response("这不是 JSON，只是一段叙述。")
    assert result["parse_fallback"] is True
    assert "这不是 JSON" in result["narration"]
    assert result["events"] == []


def test_validate_scene_payload_cleans_events():
    data = {
        "narration": "测试",
        "participants": "invalid",
        "events": [
            {"character_id": "wang_dahai", "action": "拍肩", "dialogue": "兄弟！"},
            {"dialogue": "缺少 character_id"},
            "bad",
        ],
    }
    cleaned = _validate_scene_payload(data)
    assert cleaned["participants"] == []
    assert len(cleaned["events"]) == 1
    assert cleaned["events"][0]["character_id"] == "wang_dahai"
