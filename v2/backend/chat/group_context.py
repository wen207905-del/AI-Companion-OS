"""Group chat session context — user identity, nicknames, scene visibility."""

from __future__ import annotations

from config import USER_NAME, USER_NICKNAME, load_user_profile

_ACTION_MARKERS = (
    "*", "（", "(", "抱", "摸", "吻", "亲", "压", "脱", "老婆", "妻子", "媳妇",
    "玩弄", "折腾", "弄", "躺", "骑", "坐", "搂", "蹭", " bedroom", "卧室",
    "床", "弄她", "弄他",
)

_WIFE_MARKERS = ("老婆", "妻子", "媳妇", "白柔", "柔柔")


def _wife_name(profile: dict) -> str:
    wife = profile.get("family", {}).get("wife") or {}
    if isinstance(wife, dict):
        return wife.get("name") or "白柔"
    rel = profile.get("relationships", {}).get("wife")
    if isinstance(rel, str):
        return rel
    return "白柔"


def _wife_character_id(profile: dict, persona_loader=None) -> str:
    rel = profile.get("relationships", {})
    network = rel.get("romance_network") or []
    for item in network:
        if isinstance(item, dict) and item.get("label") in ("妻子", "老婆", "合法妻子"):
            if cid := item.get("id"):
                return cid
    wife_name = _wife_name(profile)
    if persona_loader:
        for pid in getattr(persona_loader, "personas", {}) or {}:
            if persona_loader.get_display_name(pid) == wife_name:
                return pid
    return "bai_rou"


def is_scene_narration(text: str) -> bool:
    um = (text or "").strip()
    if not um:
        return False
    return any(m in um for m in _ACTION_MARKERS)


def scene_witness_ids(
    user_message: str,
    member_ids: list[str] | None,
    persona_loader=None,
) -> set[str]:
    """
    Which group members were physically present in the user's described scene.
    Default: intimate/动作场景 + 老婆 → only 白柔; others not present.
    """
    um = (user_message or "").strip()
    if not um or not is_scene_narration(um):
        return set()

    profile = load_user_profile()
    witnesses: set[str] = set()
    wife_id = _wife_character_id(profile, persona_loader)

    if any(m in um for m in _WIFE_MARKERS):
        witnesses.add(wife_id)

    if member_ids and persona_loader:
        for mid in member_ids:
            if not mid or mid == "user":
                continue
            name = persona_loader.get_display_name(mid)
            if not name or len(name) < 2:
                continue
            if name in um or f"@{name}" in um:
                witnesses.add(mid)

    return witnesses


def character_witnessed_scene(
    user_message: str,
    character_id: str,
    member_ids: list[str] | None,
    persona_loader=None,
) -> bool:
    if not is_scene_narration(user_message):
        return True
    return character_id in scene_witness_ids(user_message, member_ids, persona_loader)


def visible_user_message_for_character(
    user_message: str,
    character_id: str,
    member_ids: list[str] | None,
    persona_loader=None,
) -> str:
    """What this character can know about the user's message in-world."""
    um = (user_message or "").strip()
    if not um:
        return um
    if character_witnessed_scene(um, character_id, member_ids, persona_loader):
        return um

    profile = load_user_profile()
    witnesses = scene_witness_ids(um, member_ids, persona_loader)
    witness_names = []
    if persona_loader:
        for wid in witnesses:
            witness_names.append(persona_loader.get_display_name(wid))
    if not witness_names:
        witness_names.append(_wife_name(profile))

    who = "、".join(witness_names)
    return (
        f"（{USER_NAME}在群里发了条消息，像是在说和{who}有关的私事；"
        f"你当时不在现场，不知道具体发生了什么，也没看到任何画面）"
    )


def group_user_identity_block(
    member_ids: list[str] | None = None,
    persona_loader=None,
) -> str:
    profile = load_user_profile()
    wife = _wife_name(profile)
    lines = [
        "【用户身份——群聊唯一真人】",
        f"- {USER_NAME}（昵称{USER_NICKNAME}）：本群唯一用户，男性，云栖里·许宅主人",
        f"- {wife}：{USER_NAME}的合法妻子；用户说「老婆/妻子/媳妇」默认指{wife}",
        f"- 群消息里带「{USER_NAME}：」的是用户在说话/叙述；叙述里的「我」= {USER_NAME}",
        "- 私密的动作/场景只有**当时在场的人**知道，不在场者不能装作目击",
    ]
    if member_ids and persona_loader:
        names = []
        for mid in member_ids:
            if mid and mid != "user":
                names.append(persona_loader.get_display_name(mid))
        if names:
            lines.append(f"- 本群 AI 角色：{'、'.join(names)}")
    return "\n".join(lines)


def group_user_scene_directive(
    user_message: str,
    character_id: str,
    member_ids: list[str] | None = None,
    persona_loader=None,
) -> str:
    um = (user_message or "").strip()
    if not um:
        return ""

    profile = load_user_profile()
    wife = _wife_name(profile)
    char_name = persona_loader.get_display_name(character_id) if persona_loader else character_id
    witnessed = character_witnessed_scene(um, character_id, member_ids, persona_loader)

    if not is_scene_narration(um):
        return (
            f"【本条群消息——发送者{USER_NAME}（{USER_NICKNAME}）】\n"
            f"「{um}」\n"
            f"- 原文里的「我」若出现，指{USER_NAME}，不是{char_name}\n"
            f"- 不要抢用户动作，不要替{USER_NAME}加戏"
        )

    if witnessed:
        lines = [
            f"【私密场景——{char_name}当时在场，你知道发生了什么】",
            f"{USER_NAME}（{USER_NICKNAME}）在群里叙述的场景，你和/或{wife}等在场者亲历：",
            f"「{um}」",
            "",
            "接话时必须遵守：",
            f"1. 动作是{USER_NAME}做的，不是其他群成员做的",
            f"2. 你是亲历者/在场者，可以用第一人称回忆、害羞、接话",
            f"3. 「老婆/妻子」= {wife}（{USER_NAME}之妻）",
            "4. 不要替不在场的人（如王大海若不在）编造他们也看见的详情",
        ]
        return "\n".join(lines)

    visible = visible_user_message_for_character(
        um, character_id, member_ids, persona_loader,
    )
    witnesses = scene_witness_ids(um, member_ids, persona_loader)
    witness_names = [
        persona_loader.get_display_name(w) for w in witnesses
    ] if persona_loader else [_wife_name(profile)]
    who = "、".join(witness_names) or wife

    lines = [
        f"【重要——{char_name}不在现场，不可能知道细节】",
        f"{USER_NAME}可能在群里发了一条与{who}有关的私密叙述，但**你当时不在场**。",
        f"你在群聊里能感知到的只有：{visible}",
        "",
        "接话时必须遵守：",
        "1. 禁止描写你「看见/听到/闻到」了卧室或私密场景的具体画面——你没在",
        "2. 禁止复述用户消息里的亲密动作细节，仿佛你在场",
        f"3. 可以：懵、酸、调侃、@在场者（如{wife}）问「你俩又干啥了」、讲自己当时在别处",
        "4. 禁止把用户的行为安到你自己头上",
        f"5. 若想接话，只能基于「{USER_NAME}在群里说了点私事」这种模糊信息",
    ]
    return "\n".join(lines)
