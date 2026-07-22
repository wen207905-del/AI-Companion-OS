"""Deterministic group-turn planning layered on top of the aux LLM selector."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from chat.group_context import is_scene_narration, scene_witness_ids
from chat.group_reply_guard import wants_multi_responder


@dataclass(frozen=True)
class GroupTurnPlan:
    """A small, inspectable plan for one user message in a group chat."""

    intent: str
    responder_ids: list[str]
    roles: dict[str, str]
    max_messages: int
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


def _explicit_mentions(message: str, members: list[str], persona_loader) -> list[str]:
    text = (message or "").strip()
    if not text:
        return []

    found: list[str] = []
    for member_id in members:
        name = persona_loader.get_display_name(member_id)
        if not name:
            continue
        at_pattern = rf"@\s*{re.escape(name)}(?=$|[\s，,。！？!?、：:@])"
        # A name at the start of a sentence is also a direct address, even without @.
        lead_pattern = rf"(?:^|[。！？!?\n])\s*{re.escape(name)}(?:[，,：:\s]|$)"
        if re.search(at_pattern, text, re.IGNORECASE) or re.search(
            lead_pattern, text, re.IGNORECASE,
        ):
            found.append(member_id)
    return found


def plan_group_turn(
    user_message: str,
    members: list[str],
    persona_loader,
    *,
    candidate_responders: list[str] | None = None,
    default_max_responders: int = 1,
) -> GroupTurnPlan:
    """Build a stable plan while preserving useful aux-model recommendations.

    Direct mentions are mandatory. Scene witnesses are preferred. Ordinary messages
    always receive one main reply instead of relying on a random fallback. Explicit
    broadcast requests can fan out, but remain capped to avoid a wall of replies.
    """

    ordered_members = list(dict.fromkeys(m for m in members if m))
    if not ordered_members:
        return GroupTurnPlan("empty_group", [], {}, 0, "group_has_no_members")

    valid = set(ordered_members)
    candidates = list(dict.fromkeys(
        cid for cid in (candidate_responders or []) if cid in valid
    ))
    mentioned = _explicit_mentions(user_message, ordered_members, persona_loader)
    member_names = [persona_loader.get_display_name(cid) for cid in ordered_members]
    broadcast = wants_multi_responder(user_message, member_names)

    witnesses: list[str] = []
    if is_scene_narration(user_message):
        witness_set = scene_witness_ids(user_message, ordered_members, persona_loader)
        witnesses = [cid for cid in ordered_members if cid in witness_set]

    ranked = list(dict.fromkeys(mentioned + witnesses + candidates + ordered_members))
    if mentioned:
        intent = "direct_mention"
        max_messages = min(len(ordered_members), max(len(mentioned), default_max_responders))
        reason = "explicitly_mentioned_characters_first"
    elif broadcast:
        intent = "broadcast"
        max_messages = min(len(ordered_members), max(2, default_max_responders), 3)
        reason = "user_requested_multiple_responses"
    elif witnesses:
        intent = "scene"
        max_messages = min(len(ordered_members), max(1, default_max_responders))
        reason = "scene_witnesses_first"
    else:
        intent = "general"
        max_messages = min(len(ordered_members), max(1, default_max_responders))
        reason = "aux_candidate_or_stable_primary_fallback"

    responders = ranked[:max_messages]
    roles = {
        cid: ("primary" if index == 0 else "support")
        for index, cid in enumerate(responders)
    }
    return GroupTurnPlan(intent, responders, roles, max_messages, reason)
