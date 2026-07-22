"""Private mode resolution with ENABLE_MANUAL_MODE off."""

from chat.private_mode_handler import resolve_private_mode
from config import PERSONA_DIR
from personality.persona_loader import PersonaLoader
from services.mode_settings import set_user_mode


def test_resolve_private_mode_ignores_persisted_when_manual_off(monkeypatch, memory_db):
    import chat.private_mode_handler as pm
    from app_state import state

    monkeypatch.setattr(pm, "ENABLE_MANUAL_MODE", False)
    state.db = memory_db
    state.persona_loader = PersonaLoader(PERSONA_DIR)
    set_user_mode(memory_db, "scene")

    assert resolve_private_mode("在吗", None) == "chat"


def test_resolve_private_mode_honors_explicit_scene(monkeypatch, memory_db):
    import chat.private_mode_handler as pm
    from app_state import state

    monkeypatch.setattr(pm, "ENABLE_MANUAL_MODE", False)
    state.db = memory_db
    state.persona_loader = PersonaLoader(PERSONA_DIR)
    assert resolve_private_mode("在吗", "scene") == "scene"
