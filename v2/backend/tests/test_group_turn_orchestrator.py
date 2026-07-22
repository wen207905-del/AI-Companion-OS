from chat.group_turn_orchestrator import plan_group_turn


class PersonaStub:
    names = {"a": "白柔", "b": "夜如雪", "c": "林小小"}

    def get_display_name(self, character_id):
        return self.names[character_id]


def test_direct_mention_is_mandatory_and_primary():
    plan = plan_group_turn(
        "@夜如雪 你先说",
        ["a", "b", "c"],
        PersonaStub(),
        candidate_responders=["a"],
    )
    assert plan.intent == "direct_mention"
    assert plan.responder_ids == ["b"]
    assert plan.roles == {"b": "primary"}


def test_broadcast_allows_multiple_but_is_capped():
    plan = plan_group_turn(
        "@大家 都来说说",
        ["a", "b", "c"],
        PersonaStub(),
        candidate_responders=["c", "b", "a"],
    )
    assert plan.intent == "broadcast"
    assert plan.responder_ids == ["c", "b"]
    assert plan.max_messages == 2


def test_general_message_has_stable_non_random_fallback():
    plan = plan_group_turn(
        "今天吃什么？",
        ["a", "b", "c"],
        PersonaStub(),
        candidate_responders=[],
    )
    assert plan.intent == "general"
    assert plan.responder_ids == ["a"]


def test_multiple_direct_mentions_are_kept_even_with_default_one():
    plan = plan_group_turn(
        "@白柔，@林小小 你们两个选一个",
        ["a", "b", "c"],
        PersonaStub(),
        candidate_responders=["b"],
    )
    assert plan.responder_ids == ["a", "c"]
    assert plan.max_messages == 2
