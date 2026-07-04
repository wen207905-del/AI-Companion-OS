"""One-off helper: split v3/db.py into v3/db/ package modules."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
src = (ROOT / "v3" / "db.py").read_text(encoding="utf-8")
start = src.index("class V3Database:")
body = src[start:]
conn_start = body.index("    def __init__")
conn_end = body.index("    def create_tables")
schema_end = body.index("    # ──────── 通用工具")
rest_start = body.index("    def get_tick_id")

conn = body[conn_start:conn_end]
schema = body[conn_end:schema_end]
rest = body[rest_start:]

pkg = ROOT / "v3" / "db"
pkg.mkdir(exist_ok=True)

(pkg / "connection.py").write_text(
    '"""V3 database connection layer."""\n\n'
    "import sqlite3\n\n"
    "from v3.config import V3_DB_PATH, DB_TYPE, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME\n\n\n"
    "class ConnectionMixin:\n" + conn,
    encoding="utf-8",
)

(pkg / "schema.py").write_text(
    '"""V3 database schema creation."""\n\n\n'
    "class SchemaMixin:\n" + schema,
    encoding="utf-8",
)

(pkg / "repositories.py").write_text(
    '"""V3 database repository operations."""\n\n'
    "import json\n"
    "from typing import Optional\n\n\n"
    "class RepositoryMixin:\n" + rest,
    encoding="utf-8",
)

(pkg / "__init__.py").write_text(
    '"""V3 database package — split from legacy db.py."""\n\n'
    "from v3.db.connection import ConnectionMixin\n"
    "from v3.db.schema import SchemaMixin\n"
    "from v3.db.repositories import RepositoryMixin\n\n\n"
    "class V3Database(ConnectionMixin, SchemaMixin, RepositoryMixin):\n"
    '    """V3 database manager with SQLite/PostgreSQL backends."""\n\n'
    "    pass\n\n\n"
    "__all__ = [\"V3Database\"]\n",
    encoding="utf-8",
)

print(f"Wrote v3/db package ({len(conn)} + {len(schema)} + {len(rest)} chars)")
