"""LLM reply generation and group responder selection."""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

from app_state import state
from chat.group_context import is_scene_narration, scene_witness_ids
from chat import llm_prefs
from config import (
    CONTENT_MODE,
    GROUP_MAX_REPLY_CHARS,
    GROUP_MAX_TOKENS,
    GROUP_SKIP_EXPAND,
    GROUP_TEMPERATURE,
    LLM_INNER_THOUGHT,
    LLM_MAX_TOKENS,
    LLM_PRIVATE_MAX_TOKENS,
    LLM_STREAM,
    PRIVATE_SKIP_EXPAND,
    USER_NAME,
    USER_NICKNAME,
)
from llm import router as llm_router
from llm.router import choice_from_dict, default_choice, is_choice_available

logger = logging.getLogger("companion.reply")

OnDelta = Callable[[str], Awaitable[None]]

_INNER_LEAK_RE = re.compile(
    r"(?:^|\n)\s*(?:【(?:心声|内心(?:独白|OS)?)】|\（(?:内心|心声)[：:].*?\）)\s*",
    re.MULTILINE | re.DOTALL,
)
_INNER_PREFIX_RE = re.compile(
    r"^(?:【(?:心声|内心(?:独白|OS)?)】|(?:内心(?:独白|OS)?|心声)[：:]\s*)",
    re.IGNORECASE,
)


def _strip_leaked_inner_blocks(content: str) -> str:
    """Remove inner-thought blocks that belong in the separate 心声 field, not main reply."""
    text = (content or "").strip()
    if not text:
        return text
    text = _INNER_LEAK_RE.sub("\n", text)
    return text.strip()


def _sanitize_inner_thought(
    text: str,
    *,
    character_name: str,
    user_name: str,
) -> str:
    """Keep only valid character inner monologue; never expose system errors as 心声."""
    t = (text or "").strip()
    if not t:
        return ""
    if any(
        bad in t
        for bad in (
            "LLM 未配置",
            "LLM 调用失败",
            "LLM 超时",
            "DEEPSEEK_API_KEY",
            "QWEN_API_KEY",
            "请在 .env",
        )
    ):
        return ""
    t = _INNER_PREFIX_RE.sub("", t).strip()
    if not t:
        return ""
    user_pov_markers = (
        f"{user_name}心想",
        f"{user_name}心里",
        f"{user_name}内心",
        "用户心想",
        "用户心里",
        "汉文心想",
        "汉文心里",
        "许汉文想",
    )
    if any(m in t for m in user_pov_markers):
        return ""
    if t.startswith(f"{user_name}：") or t.startswith(f"{user_name}:"):
        return ""
    return t[:200]


def _build_inner_thought_prompt(
    *,
    name: str,
    content: str,
    chat_mode: str,
    user_message: str,
    group_name: str,
) -> str:
    public = (content or "").strip()[:400]
    user_line = (user_message or "").strip()[:120]
    if chat_mode == "group":
        scene = f"你刚才在群聊「{group_name or '群聊'}」里公开发言"
        audience = f"在场成员与{USER_NAME}"
    else:
        scene = f"你刚才在私聊里对{USER_NAME}回复"
        audience = USER_NAME

    return (
        f"你是角色「{name}」，不是用户「{USER_NAME}」。\n"
        f"{scene}，对外可见内容是：\n「{public}」\n"
        + (f"\n{USER_NAME}上一句是：「{user_line}」\n" if user_line else "")
        + f"\n请写**{name}本人**此刻的隐秘内心独白（{audience}看不到）：\n"
        f"- 第一人称「我」= {name}，绝不是{USER_NAME}\n"
        "- 不要复述已说出口的话，不要写用户的想法或用户的心声\n"
        "- 20～60字，1～2句，可含欲望/情绪\n"
        "- 只输出内心独白正文，不要标签、不要引号、不要「心声：」前缀"
    )


def resolve_llm_choice(data: dict, scope_type: str, scope_id: str) -> dict:
    db = state.db
    assert db is not None

    if data.get("type") == "set_llm":
        parsed = {
            "provider": (data.get("provider") or "").strip().lower(),
            "model": data.get("model"),
        }
    else:
        parsed = llm_prefs.parse_choice(data)
    if parsed and parsed.get("provider"):
        llm_prefs.save_pref(db, scope_type, scope_id, parsed["provider"], parsed.get("model"))
        return parsed
    saved = llm_prefs.get_pref(db, scope_type, scope_id)
    if saved:
        return saved
    default = llm_router.default_choice("main")
    return {"provider": default.provider, "model": default.model}


async def decide_responders(
    user_message: str,
    members: list[str],
    persona_loader,
    emo_engine,
) -> list[str]:
    """Use aux LLM to pick which characters should reply in group chat."""
    choice = default_choice("aux")
    if not is_choice_available(choice):
        return []

    char_profiles = []
    id_to_name = {}
    for m in members:
        p = persona_loader.get(m)
        if not p:
            continue
        name = p.get("name", m)
        id_to_name[m] = name
        emo = emo_engine.get_summary(m)
        mood = emo.get("primary_mood", "平静")
        traits = p.get("personality", {}).get("overt", {}).get("traits", [])
        trait_str = "、".join(traits[:3]) if traits else "暂无"
        occupation = p.get("base_info", {}).get("occupation", "")
        char_profiles.append(
            f"- {m}（{name}）：{occupation}；性格：{trait_str}；当前情绪：{mood}"
        )

    if not char_profiles:
        return []

    prompt = (
        f"你是群聊回复决策助手。群聊中有以下角色：\n"
        + "\n".join(char_profiles)
        + f"\n\n{USER_NAME}（{USER_NICKNAME}）说：「{user_message}」\n"
        + f"注意：消息发送者只能是{USER_NAME}；用户写的动作/场景是{USER_NAME}在做，不是角色在做。\n"
    )
    if is_scene_narration(user_message):
        witnesses = scene_witness_ids(user_message, members, persona_loader)
        if witnesses:
            wnames = [
                id_to_name.get(w, w) for w in witnesses if w in id_to_name
            ]
            prompt += (
                f"本条含私密/动作场景，仅在场者（如{'、'.join(wnames)}）亲历细节；"
                "不在场者不应装作目击，但可模糊调侃。\n"
                "优先让在场者回复；不在场者除非被@否则不必抢答。\n"
            )
    prompt += (
        "\n请判断哪些角色应该回复这条消息。判断标准：\n"
        "1. 被直接点名或@的角色 → 必须回复\n"
        "2. 话题与角色职业/专长相关 → 适合回复\n"
        "3. 情绪低落/生气的角色 → 不太想回复\n"
        "4. 角色间存在互动关系 → 可能接话\n"
        "5. 每条消息建议 1-3 个角色回复\n\n"
        "只返回角色ID列表，用逗号分隔。若无人需要回复则返回 none。\n"
        "示例：ye_ruxue, lin_xiaoxiao"
    )

    try:
        response = await llm_router.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            channel="aux",
            temperature=0.3,
            max_tokens=80,
        )
        response = response.strip().lower()
    except Exception:
        return []

    if response == "none" or not response:
        return []

    decided = []
    for token in response.split(","):
        token = token.strip().strip("'\"").strip(";")
        if token in members:
            decided.append(token)
        else:
            for m, name in id_to_name.items():
                if token == name.lower() or token in name.lower():
                    decided.append(m)
                    break

    decided = list(dict.fromkeys(decided))[:3]
    if is_scene_narration(user_message):
        witnesses = scene_witness_ids(user_message, members, persona_loader)
        if witnesses:
            mentioned = {m for m in members if id_to_name.get(m, "") in user_message or f"@{id_to_name.get(m, '')}" in user_message}
            witness_first = [m for m in decided if m in witnesses]
            others = [m for m in decided if m not in witnesses and m in mentioned]
            rest = [m for m in decided if m not in witness_first and m not in others]
            decided = witness_first + others + rest
    return decided


async def decide_character_chain(
    user_message: str,
    recent_replies: list[tuple[str, str, str]],
    members: list[str],
    persona_loader,
    emo_engine,
) -> str | None:
    """Pick one character who should respond to another character's line (not the user)."""
    choice = default_choice("aux")
    if not is_choice_available(choice) or len(recent_replies) < 1:
        return None

    target_id, target_name, target_content = recent_replies[-1]
    lines = []
    for cid, name, content in recent_replies[-3:]:
        lines.append(f"- {cid}（{name}）：「{content[:80]}」")

    profiles = []
    for m in members:
        if m == target_id:
            continue
        p = persona_loader.get(m)
        if not p:
            continue
        emo = emo_engine.get_summary(m)
        profiles.append(
            f"- {m}（{p.get('name', m)}）：情绪 {emo.get('primary_mood', '平静')}"
        )

    if not profiles:
        return None

    prompt = (
        f"群聊场景。{USER_NAME}说：「{user_message}」\n\n"
        "最近角色发言：\n" + "\n".join(lines) + "\n\n"
        "可选接话角色：\n" + "\n".join(profiles) + "\n\n"
        f"判断：是否有角色想接 {target_name} 的话（不是回复{USER_NAME}，而是跟角色互动）？\n"
        "若有，只返回一个角色ID；否则返回 none。\n"
        "示例：lin_tangtang"
    )

    try:
        response = await llm_router.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            channel="aux",
            temperature=0.3,
            max_tokens=40,
        )
        response = response.strip().lower()
    except Exception:
        return None

    if response == "none" or not response:
        return None
    token = response.split(",")[0].strip()
    if token in members and token != target_id:
        return token
    for m in members:
        p = persona_loader.get(m)
        if p and token in p.get("name", "").lower():
            if m != target_id:
                return m
    return None


def _min_reply_length() -> int:
    return 600 if CONTENT_MODE == "unrestricted" else 350


def _reply_too_short(content: str) -> bool:
    text = (content or "").strip()
    min_len = _min_reply_length()
    if len(text) < min_len:
        return True
    if text.count("「") < 3 and text.count("*") < 6:
        return len(text) < min_len + 200
    return False


def _truncate_group_reply(content: str, max_chars: int = GROUP_MAX_REPLY_CHARS) -> str:
    """Deterministic truncate at sentence/newline boundary; no LLM rewrite."""
    text = (content or "").strip()
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    best = -1
    for sep in ("\n", "。", "！", "？", "；", ".", "!", "?"):
        idx = cut.rfind(sep)
        if idx > best and idx >= int(max_chars * 0.55):
            best = idx
    if best >= 0:
        return cut[: best + 1].rstrip()
    if max_chars == 1:
        return "…"
    return cut[: max_chars - 1].rstrip() + "…"


async def _expand_short_reply(
    messages: list,
    content: str,
    llm_choice: dict | None,
) -> str:
    retry_messages = list(messages) + [
        {"role": "assistant", "content": content},
        {
            "role": "user",
            "content": (
                "【系统】上一段严重不合格：太短、缺少CG互动小说式的场景与细节。"
                "请完全重写一整篇："
                "① 开篇写时间/光线/气味/空间 ② 第三人称限定视角写角色动作与身体特写 "
                "③ 「对白」至少 4 句，每句对白前后都有 *旁白* "
                "④ 整篇不少于 800 字，亲密场景 1200 字以上 "
                "⑤ 逐点承接用户上一句的每个动作，禁止敷衍。"
            ),
        },
    ]
    expanded = await llm_router.chat_completion(
        messages=retry_messages,
        choice=llm_choice,
        temperature=0.92,
        max_tokens=LLM_PRIVATE_MAX_TOKENS,
    )
    expanded = (expanded or "").strip()
    if expanded and len(expanded) > len(content):
        return expanded
    return content


async def generate_reply(
    messages: list,
    persona: dict,
    rel_summary: dict | None = None,
    llm_choice: dict | None = None,
    on_delta: OnDelta | None = None,
    *,
    chat_mode: str = "private",
    user_message: str = "",
    group_name: str = "",
    structured_chat: bool = False,
) -> tuple[str, dict[str, Any], str]:
    """Call LLM and return (content, action, inner_thought). Streams when on_delta is set."""
    choice = choice_from_dict(llm_choice)
    name = persona.get("name", persona.get("id", "角色"))
    if not is_choice_available(choice):
        return (
            f"（{name}点了点头）嗯... 我在听呢。",
            {"type": "nod"},
            "",
        )

    try:
        use_stream = LLM_STREAM and on_delta is not None
        is_group = chat_mode == "group"
        reply_temp = GROUP_TEMPERATURE if is_group else 0.92
        max_tokens = GROUP_MAX_TOKENS if is_group else LLM_PRIVATE_MAX_TOKENS
        if use_stream:
            parts: list[str] = []
            async for delta in llm_router.chat_completion_stream(
                messages=messages,
                choice=llm_choice,
                temperature=reply_temp,
                max_tokens=max_tokens,
            ):
                parts.append(delta)
                if on_delta is not None:
                    try:
                        await on_delta(delta)
                    except Exception as ws_err:
                        logger.warning("WS stream delta send failed: %s", ws_err)
            content = "".join(parts).strip()
        else:
            content = await llm_router.chat_completion(
                messages=messages,
                choice=llm_choice,
                temperature=reply_temp,
                max_tokens=max_tokens,
            )
            content = content.strip()

        skip_expand = (
            structured_chat
            or (is_group and GROUP_SKIP_EXPAND)
            or (not is_group and PRIVATE_SKIP_EXPAND)
        )
        if (
            CONTENT_MODE == "unrestricted"
            and _reply_too_short(content)
            and not skip_expand
        ):
            logger.info("Reply too short (%d chars), expanding once", len(content))
            expanded = await _expand_short_reply(messages, content, llm_choice)
            if expanded != content and use_stream and on_delta is not None:
                extra = expanded[len(content):]
                if extra:
                    try:
                        await on_delta(extra)
                    except Exception as ws_err:
                        logger.warning("WS stream expand delta failed: %s", ws_err)
            content = expanded

        if is_group and GROUP_MAX_REPLY_CHARS > 0 and len(content) > GROUP_MAX_REPLY_CHARS:
            logger.info(
                "Group reply truncated from %d to <=%d chars",
                len(content),
                GROUP_MAX_REPLY_CHARS,
            )
            content = _truncate_group_reply(content)

        content = _strip_leaked_inner_blocks(content)

        if structured_chat:
            content, action = parse_chat_structured(content, name)
        else:
            action = infer_action(content)

        if not content:
            return (
                f"（{name}思考中...）",
                {"type": "think"},
                "",
            )

        inner_thought = ""
        rel = rel_summary or {}
        stage = int(rel.get("stage", 1))
        love = float(rel.get("love", 0))
        if LLM_INNER_THOUGHT and (stage >= 2 or love >= 20):
            thought_prompt = _build_inner_thought_prompt(
                name=name,
                content=content,
                chat_mode=chat_mode,
                user_message=user_message,
                group_name=group_name,
            )
            try:
                inner = await llm_router.chat_completion(
                    messages=[{"role": "user", "content": thought_prompt}],
                    choice=llm_choice,
                    temperature=0.6,
                    max_tokens=120,
                )
                inner_thought = _sanitize_inner_thought(
                    (inner or "").strip(),
                    character_name=name,
                    user_name=USER_NAME,
                )
            except Exception as inner_err:
                logger.warning("inner thought generation failed: %s", inner_err)
                inner_thought = ""

        return content, action, inner_thought

    except Exception as e:
        detail = str(e).strip() or type(e).__name__
        logger.warning("generate_reply failed: %s", detail)
        return (
            f"（{name}似乎想说什么，但欲言又止。）",
            {"type": "hesitate"},
            "",
        )


def infer_action(text: str) -> dict[str, str]:
    """Infer character action from reply text."""
    if any(kw in text for kw in ["哈哈", "😊", "开心", "嘻嘻"]):
        return {"type": "smile"}
    if any(kw in text for kw in ["生气", "讨厌", "滚"]):
        return {"type": "pout"}
    if any(kw in text for kw in ["晚安", "睡了"]):
        return {"type": "sleep"}
    if any(kw in text for kw in ["挥手", "再见", "拜拜"]):
        return {"type": "wave"}
    if any(kw in text for kw in ["嗯", "呃", "...", "欲言", "哼"]):
        return {"type": "hesitate"}
    return {"type": "talk"}


_ACTION_LINE_RE = re.compile(r"^【动作】(.+?)(?:\n|$)", re.MULTILINE)
_NAME_DIALOGUE_RE = re.compile(r"^(.+?)[：:]\s*[「\"](.+)[」\"]\s*$", re.DOTALL)


def parse_chat_structured(text: str, character_name: str) -> tuple[str, dict[str, Any]]:
    """
    Parse V4.1 chat mode output into display content and action object.
    Returns (content_for_bubble, action_dict).
    """
    raw = (text or "").strip()
    if not raw:
        return raw, infer_action(raw)

    action_text = ""
    body = raw
    m = _ACTION_LINE_RE.search(raw)
    if m:
        action_text = m.group(1).strip()
        body = raw[m.end():].strip()

    dialogue = body
    dm = _NAME_DIALOGUE_RE.match(body)
    if dm:
        dialogue = dm.group(2).strip()
    elif body.startswith("「") and "」" in body:
        dialogue = body.strip("「」").strip()

    content = dialogue or body or raw
    if action_text:
        action = {"type": "action", "text": action_text}
    else:
        action = infer_action(content)
    return content, action
