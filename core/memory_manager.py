import sqlite3
import os
import json
from typing import Any, Optional
from core.logger import logger

class CentralMemory:
    """
    Tiered Central Memory System for LIA.
    Uses connection pooling (single connection reuse) instead of open/close per call.
    """
    def __init__(self, db_path="memory/central_intelligence.db"):
        self.db_path = db_path
        self._conn = None
        self._init_db()

    def _get_conn(self):
        """Reuse a single connection instead of opening/closing each time."""
        if self._conn is None:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent read perf
        return self._conn

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                category TEXT,
                last_accessed DATETIME,
                frequency INTEGER DEFAULT 1
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_prompts (
                name TEXT PRIMARY KEY,
                content TEXT,
                version INTEGER,
                is_active BOOLEAN
            )
        ''')

        # Seed global system prompt
        cursor.execute('''
            INSERT OR IGNORE INTO system_prompts (name, content, version, is_active)
            VALUES (?, ?, ?, ?)
        ''', ("LIA_CORE_BRAIN", """You are the LIA Master Intelligence. 
Your primary directive is safe, efficient, and local-first automation.

RULES:
1. LOCAL-FIRST: Always use local tools (find, git, psutil) as priority.
2. SAFETY: Never delete files without explicit confirmation.
3. ACCURACY: If ambiguous, use FileAgent to search for context first.
4. CONCISE: Keep final responses short and actionable.""", 1, True))

        conn.commit()

    def store(self, key: str, value: Any, category: str = "general"):
        """Stores or updates global knowledge."""
        conn = self._get_conn()
        val_str = json.dumps(value) if not isinstance(value, str) else value
        conn.execute('''
            INSERT INTO knowledge_base (key, value, category, last_accessed)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET 
                value=excluded.value,
                last_accessed=CURRENT_TIMESTAMP,
                frequency=frequency+1
        ''', (key, val_str, category))
        conn.commit()

    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieves knowledge by key."""
        cursor = self._get_conn().cursor()
        cursor.execute("SELECT value FROM knowledge_base WHERE key=?", (key,))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except json.JSONDecodeError:
                return row[0]
        return None

    def search(self, query: str, limit: int = 10):
        """Searches knowledge base by key or category."""
        cursor = self._get_conn().cursor()
        cursor.execute(
            "SELECT key, value, category FROM knowledge_base WHERE key LIKE ? OR category LIKE ? ORDER BY frequency DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit)
        )
        return [{"key": r[0], "value": r[1], "category": r[2]} for r in cursor.fetchall()]

    def get_system_prompt(self, name="LIA_CORE_BRAIN") -> str:
        cursor = self._get_conn().cursor()
        cursor.execute("SELECT content FROM system_prompts WHERE name=? AND is_active=1", (name,))
        row = cursor.fetchone()
        return row[0] if row else ""

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

# Singleton Instance
central_memory = CentralMemory()
