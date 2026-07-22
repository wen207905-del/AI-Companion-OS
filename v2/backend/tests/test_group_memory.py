"""Group chat memory propagation tests."""

from memory.memory_manager import MemoryManager
from chat.group_memory import record_group_user_message, record_group_character_message


def test_group_user_message_recorded_for_all_present(memory_db):
    mm = MemoryManager(memory_db)
    from app_state import state
    state.memory_manager = mm

    record_group_user_message(
        ["bai_rou", "wang_dahai"],
        group_id="grp_test",
        group_name="测试群",
        content="大家晚上好",
        event_id="evt_1",
    )

    for cid in ("bai_rou", "wang_dahai"):
        group_mem = mm.recall(cid, "晚上好", limit=3, scope="group", scope_id="grp_test")
        private_mem = mm.recall(cid, "晚上好", limit=3, scope="private")
        private_prompt_mem = mm.recall_for_private_prompt(cid, "晚上好", limit=3)
        assert any("大家晚上好" in m for m in group_mem)
        assert not any("[群聊·测试群]" in m for m in private_mem)
        assert any("[群聊·测试群]" in m for m in private_prompt_mem)


def test_group_user_message_redacted_for_non_witness(memory_db):
    mm = MemoryManager(memory_db)
    from app_state import state

    class _Loader:
        personas = {"bai_rou": {}, "wang_dahai": {}}

        def get_display_name(self, cid: str) -> str:
            return {"bai_rou": "白柔", "wang_dahai": "王大海"}.get(cid, cid)

    state.memory_manager = mm
    state.persona_loader = _Loader()

    intimate = "*搂着老婆* 轻轻弄她"
    record_group_user_message(
        ["bai_rou", "wang_dahai"],
        group_id="grp_test",
        group_name="测试群",
        content=intimate,
        event_id="evt_int",
    )

    bai_mem = mm.recall("bai_rou", "弄她", limit=3, scope="group", scope_id="grp_test")
    dahai_mem = mm.recall("wang_dahai", "私事", limit=3, scope="group", scope_id="grp_test")
    assert any("弄她" in m for m in bai_mem)
    assert any("不在现场" in m for m in dahai_mem)
    assert not any("弄她" in m for m in dahai_mem)


def test_group_character_reply_witnessed_by_others(memory_db):
    mm = MemoryManager(memory_db)
    from app_state import state
    state.memory_manager = mm

    record_group_character_message(
        ["bai_rou", "wang_dahai"],
        group_id="grp_test",
        group_name="测试群",
        speaker_id="bai_rou",
        speaker_name="白柔",
        content="我做了晚饭",
        event_id="msg_1",
    )

    bai_group = mm.recall("bai_rou", "晚饭", limit=3, scope="group", scope_id="grp_test")
    dahai_group = mm.recall("wang_dahai", "晚饭", limit=3, scope="group", scope_id="grp_test")
    dahai_private = mm.recall("wang_dahai", "晚饭", limit=3, scope="private")
    dahai_private_prompt = mm.recall_for_private_prompt("wang_dahai", "晚饭", limit=3)

    assert any("白柔" in m and "晚饭" in m for m in bai_group)
    assert any("白柔" in m and "晚饭" in m for m in dahai_group)
    assert not any("[群聊·测试群]" in m for m in dahai_private)
    assert any("[群聊·测试群]" in m for m in dahai_private_prompt)
