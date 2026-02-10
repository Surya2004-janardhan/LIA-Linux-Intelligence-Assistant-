import sqlite3
import os
from core.logger import logger

class AuditManager:
    """Audit trail for all agent actions. Uses connection pooling."""
    
    def __init__(self, db_path="memory/audit_log.db"):
        self.db_path = db_path
        self._conn = None
        self._init_db()

    def _get_conn(self):
        if self._conn is None:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _init_db(self):
        conn = self._get_conn()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                agent TEXT,
                task TEXT,
                result TEXT,
                status TEXT,
                tokens_used INTEGER DEFAULT 0
            )
        ''')
        conn.commit()

    def log_action(self, agent, task, result, status="success", tokens_used=0):
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO audit_logs (agent, task, result, status, tokens_used) VALUES (?, ?, ?, ?, ?)",
                (agent, task, str(result)[:2000], status, tokens_used)  # Cap result at 2KB
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to log audit entry: {e}")

    def get_logs(self, limit=50):
        cursor = self._get_conn().cursor()
        cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        return cursor.fetchall()

    def get_agent_stats(self):
        """Returns how many tasks each agent has executed."""
        cursor = self._get_conn().cursor()
        cursor.execute("SELECT agent, COUNT(*), SUM(tokens_used) FROM audit_logs GROUP BY agent ORDER BY COUNT(*) DESC")
        return [{"agent": r[0], "tasks": r[1], "tokens": r[2] or 0} for r in cursor.fetchall()]

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

# Singleton instance
audit_manager = AuditManager()
