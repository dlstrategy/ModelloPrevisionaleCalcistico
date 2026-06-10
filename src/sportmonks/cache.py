"""Cache SQLite per risposte API Sportmonks."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class ResponseCache:
    def __init__(self, db_path: Path | str) -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _connection(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def _init_db(self) -> None:
        conn = self._connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_cache (
                cache_key TEXT PRIMARY KEY,
                response_body TEXT NOT NULL,
                fetched_at REAL NOT NULL,
                ttl_seconds INTEGER NOT NULL
            )
            """
        )
        conn.commit()

    @staticmethod
    def make_key(path: str, params: dict[str, Any] | None = None) -> str:
        payload = json.dumps({"path": path, "params": params or {}}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, cache_key: str) -> dict[str, Any] | None:
        conn = self._connection()
        row = conn.execute(
            "SELECT response_body, fetched_at, ttl_seconds FROM api_cache WHERE cache_key = ?",
            (cache_key,),
        ).fetchone()
        if row is None:
            return None
        body, fetched_at, ttl = row
        if time.time() - fetched_at > ttl:
            self.delete(cache_key)
            return None
        return json.loads(body)

    def set(self, cache_key: str, data: dict[str, Any], ttl_seconds: int) -> None:
        conn = self._connection()
        conn.execute(
            """
            INSERT OR REPLACE INTO api_cache (cache_key, response_body, fetched_at, ttl_seconds)
            VALUES (?, ?, ?, ?)
            """,
            (cache_key, json.dumps(data), time.time(), ttl_seconds),
        )
        conn.commit()

    def delete(self, cache_key: str) -> None:
        conn = self._connection()
        conn.execute("DELETE FROM api_cache WHERE cache_key = ?", (cache_key,))
        conn.commit()
