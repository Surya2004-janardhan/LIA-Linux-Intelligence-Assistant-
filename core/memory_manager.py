import sqlite3
import os
import json
from datetime import datetime
from core.logger import logger

class CentralMemory:
    """
    Tiered Central Memory System for LIA.
    Tier 1: High-speed Metadata Search (SQLite)
    Tier 2: Semantic Relationship Mapping (Knowledge Graph)
    Tier 3: Permanent Agent Lessons (Action Logs)
    """
    def __init__(self, db_path="memory/central_intelligence.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 1. Unified Knowledge (Store anything: from file summaries to user habits)
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
        
        # 2. System Prompts (The "Instruction Layer" found in high-end systems)
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
        ''', ("LIA_CORE_BRAIN", """
        You are the LIA Master Intelligence. 
        Your primary directive is safe, efficient, and local-first Linux automation.
        
        RULES OF ENGAGEMENT:
        1. LOCAL-FIRST: Always assume local tools (find, git, psutil) are the priority.
        2. SAFETY: Never delete files without explicit confirmation unless in a known 'temp' zone.
        3. ACCURACY: If a task is ambiguous, use the 'FileAgent' to search for context before acting.
        4. VERBOSITY: Keep internal thoughts detailed but final responses concise.
        """, 1, True))

        conn.commit()
        conn.close()

    def store(self, key: str, value: Any, category: str = "general"):
        """Stores or updates global knowledge."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        val_str = json.dumps(value) if not isinstance(value, str) else value
        cursor.execute('''
            INSERT INTO knowledge_base (key, value, category, last_accessed)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET 
                value=excluded.value,
                last_accessed=CURRENT_TIMESTAMP,
                frequency=frequency+1
        ''', (key, val_str, category))
        conn.commit()
        conn.close()

    def retrieve(self, key: str):
        """Retrieves knowledge by key."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM knowledge_base WHERE key=?", (key,))
        row = cursor.fetchone()
        conn.close()
        return json.loads(row[0]) if row else None

    def get_system_prompt(self, name="LIA_CORE_BRAIN"):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM system_prompts WHERE name=? AND is_active=1", (name,))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else ""

# Singleton Instance
central_memory = CentralMemory()
