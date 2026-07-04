"""V3 database connection layer."""

import sqlite3

from v3.config import V3_DB_PATH, DB_TYPE, DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME


class ConnectionMixin:
    def __init__(self, db_path: str = None):
        self._db_type = DB_TYPE
        self.db_path = db_path or V3_DB_PATH
        self.conn = None
        self._pool = None  # PostgreSQL 连接池（psycopg2 pool）

    def connect(self):
        """建立数据库连接。

        SQLite: 启用 WAL 模式 + 外键。
        PostgreSQL: 使用 psycopg2 连接池。
        """
        if self._db_type == "postgres":
            return self._connect_postgres()
        else:
            return self._connect_sqlite()

    def _connect_sqlite(self):
        """SQLite 连接。"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def _connect_postgres(self):
        """PostgreSQL 连接（使用连接池）。"""
        try:
            import psycopg2
            from psycopg2 import pool
            from psycopg2.extras import RealDictCursor
        except ImportError:
            raise ImportError(
                "psycopg2-binary 未安装。请运行: pip install psycopg2-binary"
            )

        if self._pool is None:
            self._pool = pool.SimpleConnectionPool(
                1, 10,
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                dbname=DB_NAME,
            )

        self.conn = self._pool.getconn()
        # 设置 cursor_factory 以获得类 dict 访问
        self._pg_cursor_factory = RealDictCursor
        return self.conn

    def close(self):
        """关闭数据库连接。"""
        if self.conn:
            if self._db_type == "postgres":
                if self._pool:
                    self._pool.putconn(self.conn)
                self.conn = None
            else:
                self.conn.close()
                self.conn = None

    def close_all(self):
        """关闭所有连接（PostgreSQL 连接池）。"""
        if self._db_type == "postgres" and self._pool:
            self._pool.closeall()
            self._pool = None
        elif self.conn:
            self.conn.close()
            self.conn = None

    def _execute(self, sql: str, params: tuple = None):
        """统一执行 SQL，兼容 SQLite 和 PostgreSQL。

        PostgreSQL 会自动替换：
        - DATETIME('now','localtime') → NOW()
        - INTEGER PRIMARY KEY AUTOINCREMENT → SERIAL PRIMARY KEY
        - 保留 ON CONFLICT ... DO UPDATE 语法（两者均支持）
        """
        if self._db_type == "postgres":
            sql = self._pg_adapt_sql(sql)

        cursor = self.conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor

    def _pg_adapt_sql(self, sql: str) -> str:
        """将 SQLite 特定语法转换为 PostgreSQL 语法。"""
        # datetime('now','localtime') → NOW()
        sql = sql.replace("datetime('now','localtime')", "NOW()")
        # INTEGER PRIMARY KEY AUTOINCREMENT → SERIAL PRIMARY KEY
        sql = sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
        return sql

    def _pg_cursor(self):
        """返回 PostgreSQL 兼容的 cursor，SQLite 直接使用 self.conn。"""
        if self._db_type == "postgres":
            return self.conn.cursor(cursor_factory=self._pg_cursor_factory)
        return self.conn.cursor()

    def commit(self):
        """提交事务。SQLite 直接 commit，PostgreSQL 也 commit。"""
        if self.conn:
            self.conn.commit()

    def _fetchone(self, cursor) -> dict | None:
        """统一获取一行。"""
        row = cursor.fetchone()
        if row is None:
            return None
        if self._db_type == "postgres":
            return dict(row)
        return dict(row)

    def _fetchall(self, cursor) -> list:
        """统一获取多行。"""
        rows = cursor.fetchall()
        if self._db_type == "postgres":
            return [dict(r) for r in rows]
        return [dict(r) for r in rows]

