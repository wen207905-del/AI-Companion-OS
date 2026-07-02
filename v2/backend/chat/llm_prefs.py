"""Per-chat LLM preference persistence."""

import time
from typing import Any


def ensure_table(db) -> None:
    db.execute("""
        CREATE TABLE IF NOT EXISTS chat_llm_prefs (
            scope_type TEXT NOT NULL,
            scope_id TEXT NOT NULL,
            provider TEXT NOT NULL,
            model TEXT,
            updated_at REAL NOT NULL,
            PRIMARY KEY (scope_type, scope_id)
        )
    """)
    db.commit()


def get_pref(db, scope_type: str, scope_id: str) -> dict[str, Any] | None:
    ensure_table(db)
    cur = db.execute(
        "SELECT provider, model FROM chat_llm_prefs WHERE scope_type = ? AND scope_id = ?",
        (scope_type, scope_id),
    )
    row = cur.fetchone()
    if row is None:
        return None
    provider = row["provider"]
    model = row["model"]
    if provider == "ollama":
        from config import DEEPSEEK_MODEL
        provider = "deepseek"
        model = DEEPSEEK_MODEL
        save_pref(db, scope_type, scope_id, provider, model)
    return {"provider": provider, "model": model}


def save_pref(db, scope_type: str, scope_id: str, provider: str, model: str | None) -> dict[str, Any]:
    ensure_table(db)
    now = time.time()
    db.execute(
        """
        INSERT INTO chat_llm_prefs (scope_type, scope_id, provider, model, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(scope_type, scope_id) DO UPDATE SET
            provider = excluded.provider,
            model = excluded.model,
            updated_at = excluded.updated_at
        """,
        (scope_type, scope_id, provider, model, now),
    )
    db.commit()
    return {"provider": provider, "model": model}


def parse_choice(data: dict[str, Any]) -> dict[str, Any] | None:
    llm = data.get("llm")
    if not isinstance(llm, dict):
        return None
    provider = (llm.get("provider") or "").strip().lower()
    if not provider:
        return None
    model = llm.get("model")
    if model is not None:
        model = str(model).strip() or None
    return {"provider": provider, "model": model}
