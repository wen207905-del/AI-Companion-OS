"""Pytest configuration and shared fixtures."""

import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import init_db


@pytest.fixture
def memory_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def client():
    with TestClient(__import__("main").app) as test_client:
        yield test_client
    from app_state import state
    if state.db is not None:
        state.db.close()
        state.db = None
