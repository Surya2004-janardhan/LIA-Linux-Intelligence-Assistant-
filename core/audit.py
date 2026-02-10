import sqlite3
import json
import os
import time
from core.logger import logger

class AuditManager:
    def __init__(self, db_path="memory/audit_log.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                agent TEXT,
                task TEXT,
                result TEXT,
                status TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def log_action(self, agent, task, result, status="success"):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO audit_logs (agent, task, result, status) VALUES (?, ?, ?, ?)",
                (agent, task, str(result), status)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to log audit entry: {e}")

    def get_logs(self, limit=50):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
        logs = cursor.fetchall()
        conn.close()
        return logs

# Singleton instance
audit_manager = AuditManager()
