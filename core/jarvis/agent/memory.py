"""J.A.R.V.I.S. — SQLite Memory Manager"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


class JarvisMemory:
    def __init__(self, db_path: str = "data/jarvis.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS long_term_memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    timestamp TEXT NOT NULL,
                    UNIQUE(key)
                );

                CREATE TABLE IF NOT EXISTS user_facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fact TEXT NOT NULL,
                    context TEXT,
                    timestamp TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
                CREATE INDEX IF NOT EXISTS idx_mem_key ON long_term_memory(key);
            """)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    def add_message(self, session_id: str, role: str, content: str):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (session_id, role, content, datetime.now().isoformat())
            )

    def get_history(self, session_id: str, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT role, content FROM conversations WHERE session_id = ? ORDER BY id DESC LIMIT ?",
                (session_id, limit)
            ).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def remember(self, key: str, value: str, category: str = "general") -> bool:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO long_term_memory (key, value, category, timestamp) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, timestamp=excluded.timestamp",
                (key, value, category, datetime.now().isoformat())
            )
        return True

    def recall(self, key: str) -> Optional[str]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT value FROM long_term_memory WHERE key = ?", (key,)
            ).fetchone()
        return row[0] if row else None

    def search_memory(self, query: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT key, value, category, timestamp FROM long_term_memory "
                "WHERE key LIKE ? OR value LIKE ? LIMIT 10",
                (f"%{query}%", f"%{query}%")
            ).fetchall()
        return [{"key": r[0], "value": r[1], "category": r[2], "timestamp": r[3]} for r in rows]

    def get_all_memories(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT key, value, category, timestamp FROM long_term_memory ORDER BY timestamp DESC"
            ).fetchall()
        return [{"key": r[0], "value": r[1], "category": r[2], "timestamp": r[3]} for r in rows]

    def forget(self, key: str) -> bool:
        with self._conn() as conn:
            conn.execute("DELETE FROM long_term_memory WHERE key = ?", (key,))
        return True

    def clear_session(self, session_id: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))

    def get_stats(self) -> dict:
        with self._conn() as conn:
            sessions = conn.execute("SELECT COUNT(DISTINCT session_id) FROM conversations").fetchone()[0]
            messages = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
            memories = conn.execute("SELECT COUNT(*) FROM long_term_memory").fetchone()[0]
        return {"sessions": sessions, "messages": messages, "memories": memories}
