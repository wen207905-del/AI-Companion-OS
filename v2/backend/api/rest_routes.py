"""REST API routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app_state import state
from chat.history_loader import load_group_history_for_api, load_private_history_for_api
from chat import llm_prefs
from chat.message_service import MessageError, delete_group_message, delete_private_message, edit_group_message, edit_private_message
from chat.group_broadcast import broadcast_group_created, broadcast_group_deleted
from chat.group_service import (
    add_member,
    create_group,
    delete_group,
    get_group,
    list_groups,
    remove_member,
)
from config import APP_VERSION, CONTENT_MODE, LLM_STREAM, USER_NAME, USER_NICKNAME
from image.album_store import list_album
from image.config import SILICONFLOW_API_KEY, IMAGE_CONTENT_MODE
from engine.world_clock import snapshot as world_snapshot
from llm import router as llm_router
from llm.router import choice_from_dict, is_choice_available
from personality.body_experience import build_body_experiences
from personality.photo_templates import get_photo_url, get_photo_template_meta
from services.social_relation_service import enrich_relationship_summary

router = APIRouter()


def _rel_summary(character_id: str) -> dict:
    raw = state.rel_engine.get_summary(character_id)
    if state.db is None:
        return raw
    return enrich_relationship_summary(state.db, character_id, raw)


@router.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": APP_VERSION,
        "content_mode": CONTENT_MODE,
        "llm_stream": LLM_STREAM,
        "user": {"name": USER_NAME, "nickname": USER_NICKNAME},
        "llm": llm_router.get_status(),
        "image": {
            "enabled": bool(SILICONFLOW_API_KEY),
            "provider": "siliconflow",
            "content_mode": IMAGE_CONTENT_MODE,
        },
        "world_time": world_snapshot(),
    }


@router.get("/api/world/time")
def get_world_time():
    return world_snapshot()


@router.get("/api/user")
def get_user_profile():
    return {"name": USER_NAME, "nickname": USER_NICKNAME}


@router.get("/api/llm/providers")
def list_llm_providers():
    return {
        "providers": llm_router.list_providers(),
        "default": llm_router.default_choice("main").__dict__,
    }


@router.get("/api/llm/pref/{scope_type}/{scope_id}")
def get_llm_pref(scope_type: str, scope_id: str):
    if scope_type not in ("private", "group"):
        raise HTTPException(status_code=400, detail="scope_type must be private or group")
    saved = llm_prefs.get_pref(state.db, scope_type, scope_id)
    if saved:
        return {"scope_type": scope_type, "scope_id": scope_id, "llm": saved}
    default = llm_router.default_choice("main")
    return {
        "scope_type": scope_type,
        "scope_id": scope_id,
        "llm": {"provider": default.provider, "model": default.model},
    }


@router.put("/api/llm/pref/{scope_type}/{scope_id}")
def set_llm_pref(scope_type: str, scope_id: str, body: dict):
    if scope_type not in ("private", "group"):
        raise HTTPException(status_code=400, detail="scope_type must be private or group")
    provider = (body.get("provider") or "").strip().lower()
    model = body.get("model")
    if not provider:
        raise HTTPException(status_code=400, detail="provider is required")
    choice = choice_from_dict({"provider": provider, "model": model})
    if not is_choice_available(choice):
        raise HTTPException(
            status_code=400,
            detail=f"provider {provider} is not configured or unavailable",
        )
    saved = llm_prefs.save_pref(state.db, scope_type, scope_id, choice.provider, choice.model)
    return {"scope_type": scope_type, "scope_id": scope_id, "llm": saved}


@router.get("/api/characters")
def list_characters():
    result = []
    for pid, persona in state.persona_loader.personas.items():
        summary = _rel_summary(pid)
        emo_summary = state.emo_engine.get_summary(pid)
        arousal_summary = (
            state.arousal_engine.get_summary(pid)
            if state.arousal_engine
            else {}
        )
        result.append({
            "id": pid,
            "name": persona.get("name", pid),
            "type": persona.get("type", ""),
            "stage": summary.get("stage", 1),
            "stage_name": summary.get("stage_name", "陌生人"),
            "love": summary.get("love", 0),
            "social_relation_label": summary.get("social_relation_label", ""),
            "social_relation_type": summary.get("social_relation_type", ""),
            "affection_score": summary.get("affection_score"),
            "affection_grade": summary.get("affection_grade", ""),
            "affection_label": summary.get("affection_label", ""),
            "current_activity": summary.get("current_activity", "日常"),
            "is_friendship": summary.get("is_friendship", False),
            "mood": emo_summary.get("primary_mood", "平静"),
            "gender": persona.get("base_info", {}).get("gender", ""),
            "occupation": (
                persona.get("base_info", {}).get("occupation")
                or persona.get("base_info", {}).get("identity")
                or ""
            ),
            "age": persona.get("base_info", {}).get("age"),
            "arousal": arousal_summary.get("level", 0),
            "arousal_label": arousal_summary.get("label", "平静"),
            "avatar_url": get_photo_url(pid),
        })
    return {"characters": result}


@router.get("/api/character/{character_id}")
def get_character(character_id: str):
    persona = state.persona_loader.get(character_id)
    if not persona:
        raise HTTPException(status_code=404, detail="character not found")

    rel = _rel_summary(character_id)
    emo = state.emo_engine.get_summary(character_id)
    arousal = (
        state.arousal_engine.get_summary(character_id)
        if state.arousal_engine
        else {}
    )
    style = state.persona_loader.get_chat_style(character_id)
    growth = state.growth_engine.get_profile(character_id) if state.growth_engine else {}
    memories = []
    if state.memory_manager:
        memories = state.memory_manager.recent_for_character(character_id, limit=5)

    album = list_album(character_id, limit=12)

    return {
        "id": character_id,
        "persona": persona,
        "relationship": rel,
        "emotion": emo,
        "arousal": arousal,
        "chat_style": style,
        "growth": growth,
        "recent_memories": memories,
        "album": album,
        "image_enabled": bool(SILICONFLOW_API_KEY),
        "body_experiences": build_body_experiences(persona, rel),
        "photo_template": get_photo_template_meta(character_id),
    }


@router.get("/api/chat/{character_id}/history")
def get_chat_history(character_id: str, limit: int = 50):
    if not state.persona_loader.get(character_id):
        raise HTTPException(status_code=404, detail="character not found")
    messages = load_private_history_for_api(state.db, character_id, limit=limit)
    return {"character_id": character_id, "messages": messages}


@router.patch("/api/chat/{character_id}/messages/{message_id}")
def patch_private_message(character_id: str, message_id: str, body: dict):
    if not state.persona_loader.get(character_id):
        raise HTTPException(status_code=404, detail="character not found")
    content = body.get("content", "")
    try:
        updated = edit_private_message(state.db, character_id, message_id, content)
    except MessageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return updated


@router.delete("/api/chat/{character_id}/messages/{message_id}")
def remove_private_message(character_id: str, message_id: str):
    if not state.persona_loader.get(character_id):
        raise HTTPException(status_code=404, detail="character not found")
    if not delete_private_message(state.db, character_id, message_id):
        raise HTTPException(status_code=404, detail="message not found")
    return {"ok": True, "id": message_id}


@router.get("/api/group/{group_id}/history")
def get_group_history(group_id: str, limit: int = 100):
    cur = state.db.execute("SELECT id FROM group_chats WHERE id = ?", (group_id,))
    if cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="group not found")
    messages = load_group_history_for_api(state.db, group_id, limit=limit)
    return {"group_id": group_id, "messages": messages}


@router.patch("/api/group/{group_id}/messages/{message_id}")
def patch_group_message(group_id: str, message_id: str, body: dict):
    cur = state.db.execute("SELECT id FROM group_chats WHERE id = ?", (group_id,))
    if cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="group not found")
    content = body.get("content", "")
    try:
        updated = edit_group_message(state.db, group_id, message_id, content)
    except MessageError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return updated


@router.delete("/api/group/{group_id}/messages/{message_id}")
def remove_group_message(group_id: str, message_id: str):
    cur = state.db.execute("SELECT id FROM group_chats WHERE id = ?", (group_id,))
    if cur.fetchone() is None:
        raise HTTPException(status_code=404, detail="group not found")
    if not delete_group_message(state.db, group_id, message_id):
        raise HTTPException(status_code=404, detail="message not found")
    return {"ok": True, "id": message_id}


@router.get("/api/groups")
def api_list_groups():
    return {"groups": list_groups(state.db)}


@router.get("/api/group/{group_id}")
def api_get_group(group_id: str):
    group = get_group(state.db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="group not found")
    return group


@router.post("/api/groups")
def api_create_group(body: dict, background_tasks: BackgroundTasks):
    name = (body.get("name") or "新群聊").strip()
    member_ids = body.get("member_ids") or body.get("members") or []
    if not isinstance(member_ids, list):
        raise HTTPException(status_code=400, detail="member_ids must be a list")
    try:
        group = create_group(state.db, name, member_ids, state.persona_loader)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    background_tasks.add_task(broadcast_group_created, group)
    return group


@router.post("/api/group/{group_id}/members")
def api_add_group_member(group_id: str, body: dict):
    char_id = (body.get("character_id") or "").strip()
    if not char_id:
        raise HTTPException(status_code=400, detail="character_id is required")
    if not add_member(state.db, group_id, char_id):
        raise HTTPException(status_code=404, detail="group or character not found")
    return get_group(state.db, group_id)


@router.delete("/api/group/{group_id}/members/{character_id}")
def api_remove_group_member(group_id: str, character_id: str):
    if not remove_member(state.db, group_id, character_id):
        raise HTTPException(status_code=404, detail="group not found")
    return get_group(state.db, group_id)


@router.delete("/api/group/{group_id}")
def api_delete_group(group_id: str, background_tasks: BackgroundTasks):
    if not delete_group(state.db, group_id):
        raise HTTPException(status_code=404, detail="group not found")
    background_tasks.add_task(broadcast_group_deleted, group_id)
    return {"ok": True, "id": group_id}


@router.get("/api/dashboard")
def dashboard():
    characters = []
    for pid in state.persona_loader.personas:
        rel = _rel_summary(pid)
        emo = state.emo_engine.get_summary(pid)
        growth = state.growth_engine.get_profile(pid) if state.growth_engine else {}
        characters.append({
            "id": pid,
            "name": state.persona_loader.get_display_name(pid),
            "stage": rel.get("stage", 1),
            "stage_name": rel.get("stage_name", "陌生人"),
            "love": rel.get("love", 0),
            "social_relation_label": rel.get("social_relation_label", ""),
            "affection_grade": rel.get("affection_grade", ""),
            "affection_label": rel.get("affection_label", ""),
            "current_activity": rel.get("current_activity", "日常"),
            "mood": emo.get("primary_mood", "平静"),
            "happy": emo.get("happy", 50),
            "level": growth.get("level", 1),
            "xp": growth.get("xp", 0),
        })

    return {
        "total_characters": len(characters),
        "active_group_chats": len(state.group_members),
        "characters": characters,
    }


@router.get("/api/v4/mode")
def get_mode():
    from services.mode_settings import get_user_mode
    return {"mode": get_user_mode(state.db)}


@router.put("/api/v4/mode")
def put_mode(body: dict):
    from services.mode_settings import set_user_mode
    mode = set_user_mode(
        state.db,
        body.get("mode") or "chat",
        active_character_id=body.get("active_character_id"),
    )
    return {"mode": mode}


@router.post("/api/v4/chat")
async def api_v4_chat(body: dict):
    character_id = (body.get("character_id") or "").strip()
    message = (body.get("message") or "").strip()
    if not character_id or not message:
        raise HTTPException(status_code=400, detail="character_id and message required")
    persona = state.persona_loader.get(character_id)
    if not persona:
        raise HTTPException(status_code=404, detail="character not found")

    from chat.private_mode_handler import build_private_llm_messages
    from chat.reply_service import generate_reply

    llm_messages = build_private_llm_messages(character_id, persona, message)
    rel = _rel_summary(character_id)
    content, action, inner_thought = await generate_reply(
        llm_messages,
        persona,
        rel_summary=rel,
        structured_chat=True,
        user_message=message,
    )
    return {
        "mode": "chat",
        "speaker": character_id,
        "action": action.get("text") if isinstance(action, dict) else "",
        "dialogue": content,
        "inner_thought": inner_thought,
        "action_obj": action,
    }


@router.post("/api/v4/scene")
async def api_v4_scene(body: dict):
    text = (body.get("text") or body.get("message") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text required")
    from services.scene_mode_service import generate_scene_response
    result = await generate_scene_response(text, body.get("llm"))
    return result


@router.get("/api/v4/character-dm/list")
def api_character_dm_list():
    from services.character_dm_service import list_conversations
    if not state.db:
        return {"conversations": []}
    return {"conversations": list_conversations(state.db)}


@router.get("/api/v4/character-dm/{conversation_id}")
def api_character_dm_detail(conversation_id: str):
    from services.character_dm_service import get_conversation_detail
    if not state.db:
        raise HTTPException(status_code=503, detail="db unavailable")
    detail = get_conversation_detail(state.db, conversation_id)
    if not detail:
        raise HTTPException(status_code=404, detail="conversation not found")
    return detail
