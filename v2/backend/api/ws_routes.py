"""WebSocket handlers for private and group chat."""

from __future__ import annotations

import asyncio
import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.ws_hub import hub
from app_state import state
from chat.context_builder import boundary_hint_for, memory_block_for, memory_block_for_group, status_block_for
from chat.group_service import maybe_run_character_chain
from chat.history_loader import load_group_history_for_character, load_private_history
from chat.message_service import MessageError
from chat.prompt_builder import PromptBuilder
from chat.regenerate_service import prepare_group_regenerate, prepare_private_regenerate
from chat.reply_service import decide_responders, resolve_llm_choice
from chat.stream_delivery import deliver_character_reply
from chat.stat_snapshot import build_stat_update
from chat import llm_prefs
from engine.world_clock import now as world_now, snapshot as world_snapshot
from event.event_bus import event_bus
from llm import router as llm_router
from config import USER_NAME

router = APIRouter()


async def _emit_stat(room: str, data: dict) -> None:
    await hub.send_rooms([room, "global"], data)


@router.websocket("/ws/chat/{character_id}")
async def private_chat(websocket: WebSocket, character_id: str):
    await websocket.accept()

    persona = state.persona_loader.get(character_id)
    if not persona:
        await websocket.send_json({"type": "error", "message": "角色不存在"})
        await websocket.close()
        return

    display_name = persona.get("name", character_id)
    rel = state.rel_engine.get_summary(character_id)
    emo = state.emo_engine.get_summary(character_id)
    init_llm = llm_prefs.get_pref(state.db, "private", character_id)
    if not init_llm:
        default = llm_router.default_choice("main")
        init_llm = {"provider": default.provider, "model": default.model}

    room = f"private:{character_id}"
    hub.join(websocket, "global")
    hub.join(websocket, room)

    async def emit(data: dict) -> None:
        await hub.send_room(room, data)

    await websocket.send_json({
        "type": "init",
        "character": {
            "id": character_id,
            "name": display_name,
            "stage_name": rel.get("stage_name", "陌生人"),
            "mood": emo.get("primary_mood", "平静"),
        },
        "llm": init_llm,
        "world_time": world_snapshot(),
    })

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "set_llm":
                llm_choice = resolve_llm_choice(data, "private", character_id)
                await emit({"type": "llm_updated", "llm": llm_choice})
                continue

            if data.get("type") == "regenerate":
                msg_id = (data.get("message_id") or "").strip()
                if not msg_id:
                    continue
                llm_choice = resolve_llm_choice(data, "private", character_id)
                try:
                    user_message = prepare_private_regenerate(
                        state.db, character_id, msg_id,
                    )
                except MessageError as e:
                    await emit({"type": "error", "message": str(e)})
                    continue

                await emit({
                    "type": "regenerate_start",
                    "message_id": msg_id,
                })
                await emit({
                    "type": "typing",
                    "character_id": character_id,
                    "character_name": display_name,
                })

                regen_hint = (
                    "【重新生成】用户对刚才的回复不满意。"
                    "请针对" + USER_NAME + "同一句话换一种说法重新接话，不要重复上一轮措辞与动作描写。"
                )
                boundary_hint = boundary_hint_for(persona, user_message, character_id)
                if boundary_hint:
                    boundary_hint = boundary_hint + "\n\n" + regen_hint
                else:
                    boundary_hint = regen_hint
                rel = state.rel_engine.get_summary(character_id)
                emo = state.emo_engine.get_summary(character_id)
                style = state.persona_loader.get_chat_style(character_id)
                history = load_private_history(state.db, character_id, limit=30)
                memory_text = memory_block_for(character_id, user_message, scope="private")
                status_text = status_block_for(
                    character_id, persona, rel, emo,
                    user_message=user_message, scope="private",
                )
                builder = PromptBuilder(persona)
                llm_messages = builder.build_private_messages(
                    rel, emo, style, history,
                    memory_text=memory_text,
                    boundary_hint=boundary_hint,
                    status_text=status_text,
                    user_message=user_message,
                )

                def _save_private_regen(rid, content, action, inner_thought, ts):
                    state.db.execute(
                        """INSERT INTO private_messages
                           (id, character_id, sender_type, content, action, inner_thought, timestamp)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (rid, character_id, "character", content,
                         json.dumps(action, ensure_ascii=False) if action else None,
                         inner_thought, ts),
                    )
                    state.db.commit()

                await deliver_character_reply(
                    room,
                    reply_id=msg_id,
                    llm_messages=llm_messages,
                    persona=persona,
                    rel_summary=rel,
                    llm_choice=llm_choice,
                    ws_meta={
                        "character_id": character_id,
                        "sender_type": "character",
                        "sender_id": character_id,
                    },
                    save_to_db=_save_private_regen,
                )
                await emit({
                    "type": "typing_end",
                    "character_id": character_id,
                })
                continue

            user_message = data.get("message", "").strip()
            if not user_message:
                continue

            llm_choice = resolve_llm_choice(data, "private", character_id)

            await emit({
                "type": "typing",
                "character_id": character_id,
                "character_name": display_name,
            })

            rel_before = state.rel_engine.get_summary(character_id)
            emo_before = state.emo_engine.get_summary(character_id)
            arousal_before = (
                state.arousal_engine.get_summary(character_id)
                if state.arousal_engine
                else None
            )
            growth_before = (
                state.growth_engine.get_profile(character_id)
                if state.growth_engine
                else None
            )

            event = event_bus.create_event(
                event_type="conversation",
                participants=["user", character_id],
                raw_input=user_message,
                metadata={"display_name": display_name},
            )
            event_bus.dispatch(event)

            stat_payload = build_stat_update(
                character_id,
                rel_before,
                state.rel_engine.get_summary(character_id),
                emo_before,
                state.emo_engine.get_summary(character_id),
                growth_before,
                state.growth_engine.get_profile(character_id)
                if state.growth_engine
                else None,
                arousal_before,
                state.arousal_engine.get_summary(character_id)
                if state.arousal_engine
                else None,
            )

            client_id = data.get("client_id")
            await emit({
                "type": "user_message_saved",
                "id": event.event_id,
                "client_id": client_id,
                "content": user_message,
                "timestamp": event.timestamp,
                "sender_type": "user",
            })

            boundary_hint = boundary_hint_for(persona, user_message, character_id)
            rel = state.rel_engine.get_summary(character_id)
            emo = state.emo_engine.get_summary(character_id)
            style = state.persona_loader.get_chat_style(character_id)
            history = load_private_history(state.db, character_id, limit=30)
            memory_text = memory_block_for(character_id, user_message, scope="private")
            status_text = status_block_for(
                character_id, persona, rel, emo,
                user_message=user_message, scope="private",
            )
            builder = PromptBuilder(persona)
            llm_messages = builder.build_private_messages(
                rel, emo, style, history,
                memory_text=memory_text,
                boundary_hint=boundary_hint,
                status_text=status_text,
                user_message=user_message,
            )

            reply_id = f"msg_{uuid.uuid4().hex[:12]}"

            def _save_private(rid, content, action, inner_thought, ts):
                state.db.execute(
                    """INSERT INTO private_messages
                       (id, character_id, sender_type, content, action, inner_thought, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (rid, character_id, "character", content,
                     json.dumps(action, ensure_ascii=False) if action else None,
                     inner_thought, ts),
                )
                state.db.commit()

            await deliver_character_reply(
                room,
                reply_id=reply_id,
                llm_messages=llm_messages,
                persona=persona,
                rel_summary=rel,
                llm_choice=llm_choice,
                ws_meta={
                    "character_id": character_id,
                    "sender_type": "character",
                    "sender_id": character_id,
                },
                save_to_db=_save_private,
            )

            await _emit_stat(room, stat_payload)

            await emit({
                "type": "typing_end",
                "character_id": character_id,
            })

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        hub.leave_all(websocket)


@router.websocket("/ws/group/{group_id}")
async def group_chat(websocket: WebSocket, group_id: str):
    await websocket.accept()

    cur = state.db.execute("SELECT id, name FROM group_chats WHERE id = ?", (group_id,))
    group = cur.fetchone()
    if not group:
        await websocket.send_json({"type": "error", "message": "群聊不存在"})
        await websocket.close()
        return

    group_name = group["name"]
    members = state.group_members.get(group_id, set())
    if not members:
        cur = state.db.execute(
            "SELECT character_id FROM group_chat_members WHERE chat_id = ?",
            (group_id,),
        )
        members = {row["character_id"] for row in cur.fetchall()}
        state.group_members[group_id] = members

    init_llm = llm_prefs.get_pref(state.db, "group", group_id)
    if not init_llm:
        default = llm_router.default_choice("main")
        init_llm = {"provider": default.provider, "model": default.model}

    room = f"group:{group_id}"
    hub.join(websocket, "global")
    hub.join(websocket, room)

    async def emit(data: dict) -> None:
        await hub.send_room(room, data)

    await websocket.send_json({
        "type": "init",
        "group": {"id": group_id, "name": group_name, "members": list(members)},
        "llm": init_llm,
        "world_time": world_snapshot(),
    })

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "set_llm":
                llm_choice = resolve_llm_choice(data, "group", group_id)
                await emit({"type": "llm_updated", "llm": llm_choice})
                continue

            if data.get("type") == "regenerate":
                msg_id = (data.get("message_id") or "").strip()
                if not msg_id:
                    continue
                llm_choice = resolve_llm_choice(data, "group", group_id)
                try:
                    char_id, user_message = prepare_group_regenerate(
                        state.db, group_id, msg_id,
                    )
                except MessageError as e:
                    await emit({"type": "error", "message": str(e)})
                    continue

                persona = state.persona_loader.get(char_id)
                if not persona:
                    await emit({"type": "error", "message": "角色不存在"})
                    continue

                await emit({
                    "type": "regenerate_start",
                    "message_id": msg_id,
                    "group_id": group_id,
                    "character_id": char_id,
                })
                await emit({
                    "type": "typing",
                    "group_id": group_id,
                    "character_id": char_id,
                    "character_name": persona.get("name", char_id),
                })

                regen_hint = (
                    "【重新生成】用户对刚才的回复不满意。"
                    "请针对" + USER_NAME + "同一句话换一种说法重新接话，不要重复上一轮措辞。"
                )
                boundary_hint = boundary_hint_for(persona, user_message, char_id)
                boundary_hint = (boundary_hint + "\n\n" + regen_hint) if boundary_hint else regen_hint
                group_rel = state.rel_engine.get_summary(char_id)
                group_emo = state.emo_engine.get_summary(char_id)
                memory_text = memory_block_for_group(char_id, user_message, group_id)
                status_text = status_block_for(
                    char_id, persona, group_rel, group_emo,
                    user_message=user_message, scope="group", group_name=group_name,
                )
                other_names = [
                    state.persona_loader.get_display_name(m)
                    for m in members if m != char_id
                ]
                group_hist = load_group_history_for_character(
                    state.db, group_id, state.persona_loader, char_id,
                    list(members), limit=20,
                )
                builder = PromptBuilder(persona)
                llm_messages = builder.build_group_messages(
                    group_emo, group_rel, group_name, other_names, user_message,
                    history=group_hist,
                    memory_text=memory_text,
                    boundary_hint=boundary_hint,
                    status_text=status_text,
                    member_ids=list(members),
                    character_id=char_id,
                    persona_loader=state.persona_loader,
                )

                def _save_group_regen(rid, content, action, inner_thought, ts):
                    state.db.execute(
                        """INSERT INTO group_messages
                           (id, chat_id, sender_type, sender_id, content, action, inner_thought, timestamp)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (rid, group_id, "character", char_id,
                         content,
                         json.dumps(action, ensure_ascii=False) if action else None,
                         inner_thought, ts),
                    )
                    state.db.commit()

                await emit({
                    "type": "typing_end",
                    "group_id": group_id,
                    "character_id": char_id,
                })

                await deliver_character_reply(
                    room,
                    reply_id=msg_id,
                    llm_messages=llm_messages,
                    persona=persona,
                    rel_summary=group_rel,
                    llm_choice=llm_choice,
                    ws_meta={
                        "group_id": group_id,
                        "character_id": char_id,
                        "sender_type": "character",
                        "sender_id": char_id,
                    },
                    save_to_db=_save_group_regen,
                    memory_scope="group",
                    memory_scope_id=group_id,
                    present_members=list(members),
                    group_name=group_name,
                )
                continue

            user_message = data.get("message", "").strip()
            if not user_message:
                continue

            if not members:
                await emit({
                    "type": "error",
                    "message": "群里还没有角色，请先添加成员",
                })
                continue

            llm_choice = resolve_llm_choice(data, "group", group_id)

            client_id = data.get("client_id")
            user_msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            msg_ts = world_now()
            state.db.execute(
                """INSERT INTO group_messages
                   (id, chat_id, sender_type, sender_id, content, timestamp)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (user_msg_id, group_id, "user", "user", user_message, msg_ts),
            )
            state.db.commit()

            await emit({
                "type": "message",
                "id": user_msg_id,
                "client_id": client_id,
                "group_id": group_id,
                "sender_type": "user",
                "sender_id": "user",
                "content": user_message,
                "timestamp": msg_ts,
            })

            stat_snapshots_before: dict[str, dict] = {}
            for cid in members:
                stat_snapshots_before[cid] = {
                    "rel": state.rel_engine.get_summary(cid),
                    "emo": state.emo_engine.get_summary(cid),
                    "arousal": (
                        state.arousal_engine.get_summary(cid)
                        if state.arousal_engine
                        else None
                    ),
                    "growth": (
                        state.growth_engine.get_profile(cid)
                        if state.growth_engine
                        else None
                    ),
                }

            event = event_bus.create_event(
                event_type="conversation",
                participants=["user"] + list(members),
                raw_input=user_message,
                metadata={"group_id": group_id, "group_name": group_name},
                timestamp=msg_ts,
            )
            event_bus.dispatch(event)

            responders = await decide_responders(
                user_message, list(members), state.persona_loader, state.emo_engine,
            )
            responders = responders[:2]

            if not responders:
                await emit({"type": "reply_batch_end", "group_id": group_id})
                continue

            recent_replies: list[tuple[str, str, str]] = []
            member_list = list(members)

            for char_id in responders:
                p = state.persona_loader.get(char_id)
                await emit({
                    "type": "typing",
                    "group_id": group_id,
                    "character_id": char_id,
                    "character_name": p.get("name", char_id) if p else char_id,
                })

            prior_in_batch: list[tuple[str, str]] = []

            for char_id in responders:
                try:
                    persona = state.persona_loader.get(char_id)
                    if not persona:
                        await emit({
                            "type": "typing_end",
                            "group_id": group_id,
                            "character_id": char_id,
                        })
                        continue

                    group_hist = load_group_history_for_character(
                        state.db, group_id, state.persona_loader, char_id,
                        member_list, limit=20,
                    )
                    boundary_hint = boundary_hint_for(persona, user_message, char_id)
                    group_rel = state.rel_engine.get_summary(char_id)
                    group_emo = state.emo_engine.get_summary(char_id)
                    memory_text = memory_block_for_group(char_id, user_message, group_id)
                    status_text = status_block_for(
                        char_id, persona, group_rel, group_emo,
                        user_message=user_message, scope="group", group_name=group_name,
                    )
                    other_names = [
                        state.persona_loader.get_display_name(m)
                        for m in members if m != char_id
                    ]
                    builder = PromptBuilder(persona)
                    llm_messages = builder.build_group_messages(
                        group_emo, group_rel, group_name, other_names, user_message,
                        history=group_hist,
                        memory_text=memory_text,
                        boundary_hint=boundary_hint,
                        status_text=status_text,
                        member_ids=member_list,
                        prior_replies=prior_in_batch.copy() if prior_in_batch else None,
                        character_id=char_id,
                        persona_loader=state.persona_loader,
                    )

                    reply_id = f"msg_{uuid.uuid4().hex[:12]}"

                    def _save_group(rid, content, action, inner_thought, ts, _cid=char_id):
                        state.db.execute(
                            """INSERT INTO group_messages
                               (id, chat_id, sender_type, sender_id, content, action, inner_thought, timestamp)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (rid, group_id, "character", _cid,
                             content,
                             json.dumps(action, ensure_ascii=False) if action else None,
                             inner_thought, ts),
                        )
                        state.db.commit()

                    await emit({
                        "type": "typing_end",
                        "group_id": group_id,
                        "character_id": char_id,
                    })

                    reply_content = await deliver_character_reply(
                        room,
                        reply_id=reply_id,
                        llm_messages=llm_messages,
                        persona=persona,
                        rel_summary=group_rel,
                        llm_choice=llm_choice,
                        ws_meta={
                            "group_id": group_id,
                            "character_id": char_id,
                            "sender_type": "character",
                            "sender_id": char_id,
                        },
                        save_to_db=_save_group,
                        memory_scope="group",
                        memory_scope_id=group_id,
                        present_members=list(members),
                        group_name=group_name,
                    )

                    snap = stat_snapshots_before.get(char_id)
                    if snap:
                        await _emit_stat(
                            room,
                            build_stat_update(
                                char_id,
                                snap["rel"],
                                state.rel_engine.get_summary(char_id),
                                snap["emo"],
                                state.emo_engine.get_summary(char_id),
                                snap["growth"],
                                state.growth_engine.get_profile(char_id)
                                if state.growth_engine
                                else None,
                                snap.get("arousal"),
                                state.arousal_engine.get_summary(char_id)
                                if state.arousal_engine
                                else None,
                            ),
                        )

                    if reply_content:
                        cname = persona.get("name", char_id)
                        recent_replies.append((char_id, cname, reply_content))
                        prior_in_batch.append((cname, reply_content))
                except Exception:
                    await emit({
                        "type": "typing_end",
                        "group_id": group_id,
                        "character_id": char_id,
                    })

            await maybe_run_character_chain(
                room,
                group_id=group_id,
                group_name=group_name,
                members=members,
                user_message=user_message,
                recent_replies=recent_replies,
                llm_choice=llm_choice,
            )

            await emit({"type": "reply_batch_end", "group_id": group_id})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        hub.leave_all(websocket)
