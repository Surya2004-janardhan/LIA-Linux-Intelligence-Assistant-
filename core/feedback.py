"""
WIA Feedback System — Local command rating and history-based RAG.

Stores every successful command with user ratings.
When a similar query comes in, retrieves the known-working command
instead of generating a new one (Retrieval-Augmented Generation).
"""
import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict
from core.logger import logger


from memory.vector_store import vector_store

class FeedbackManager:
    """
    Local feedback loop:
    1. Stores every executed command with query + result
    2. Users can upvote/downvote
    3. On similar queries, retrieves high-rated past commands (RAG)
    """
    
    def __init__(self, db_path="memory/feedback.db"):
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
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS command_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                query TEXT,
                agent TEXT,
                tool TEXT,
                command TEXT,
                result TEXT,
                rating INTEGER DEFAULT 0,
                success BOOLEAN DEFAULT 1
            );
            
            CREATE INDEX IF NOT EXISTS idx_query ON command_history(query);
            CREATE INDEX IF NOT EXISTS idx_rating ON command_history(rating DESC);
            
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                query TEXT,
                response TEXT,
                rating INTEGER,
                comment TEXT
            );
        ''')
        conn.commit()
    
    # ─── COMMAND HISTORY ──────────────────────────────────────────
    
    def record_command(self, query: str, agent: str, tool: str, 
                       command: str, result: str, success: bool = True):
        """Records a command execution for future RAG retrieval."""
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO command_history (query, agent, tool, command, result, success) VALUES (?, ?, ?, ?, ?, ?)",
                (query, agent, tool, command, result[:2000], success)
            )
            conn.commit()
            
            # Also add to vector store if successful
            if success:
                vector_store.add_text(query, {
                    "query": query, "agent": agent, "tool": tool, "command": command
                })
        except Exception as e:
            logger.error(f"Failed to record command: {e}")
    
    def rate_last_command(self, rating: int):
        """Rate the most recent command (1=bad, 5=great)."""
        try:
            conn = self._get_conn()
            conn.execute(
                "UPDATE command_history SET rating = ? WHERE id = (SELECT MAX(id) FROM command_history)",
                (max(1, min(5, rating)),)
            )
            conn.commit()
            return f"✅ Rated last command: {'⭐' * rating}"
        except Exception as e:
            return f"Rating failed: {e}"
    
    def find_similar(self, query: str, min_rating: int = 3, limit: int = 3) -> List[Dict]:
        """
        RAG: Find past commands that match the current query using Vector Similarity.
        """
        try:
            # 1. Try Vector Search (Best accuracy)
            vector_results = vector_store.search_text(query, k=limit)
            if vector_results:
                results = []
                for res in vector_results:
                    # Filter by "distance" (score) if needed
                    if res["score"] < 1.0: # Heuristic threshold for nomic-embed
                        results.append(res["metadata"])
                if results:
                    return results

            # 2. Fallback to SQLite keyword matching
            cursor = self._get_conn().cursor()
            stop_words = {"the", "a", "an", "is", "are", "do", "how", "what", "please"}
            keywords = [w.lower() for w in query.split() if w.lower() not in stop_words and len(w) > 2]
            
            if not keywords:
                return []
            
            conditions = " OR ".join(["query LIKE ?" for _ in keywords])
            params = [f"%{kw}%" for kw in keywords]
            params.extend([min_rating, limit])
            
            cursor.execute(f"""
                SELECT query, agent, tool, command, result, rating 
                FROM command_history 
                WHERE ({conditions}) AND rating >= ? AND success = 1
                ORDER BY rating DESC LIMIT ?
            """, params)
            
            return [{"query": r[0], "agent": r[1], "tool": r[2], "command": r[3], "result": r[4]} for r in cursor.fetchall()]
        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return []
    
    # ─── USER FEEDBACK ────────────────────────────────────────────
    
    def submit_feedback(self, query: str, response: str, rating: int, comment: str = ""):
        """User upvote/downvote on overall response quality."""
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT INTO feedback (query, response, rating, comment) VALUES (?, ?, ?, ?)",
                (query, response[:2000], max(1, min(5, rating)), comment)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Feedback submission failed: {e}")
            return False
    
    def get_feedback_stats(self) -> Dict:
        """Returns aggregated feedback stats for prompt tuning."""
        try:
            cursor = self._get_conn().cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    AVG(rating) as avg_rating,
                    SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as positive,
                    SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as negative
                FROM feedback
            """)
            row = cursor.fetchone()
            return {
                "total_feedback": row[0],
                "avg_rating": round(row[1] or 0, 2),
                "positive": row[2] or 0,
                "negative": row[3] or 0
            }
        except Exception:
            return {"total_feedback": 0, "avg_rating": 0, "positive": 0, "negative": 0}
    
    def get_history(self, limit: int = 20) -> List[Dict]:
        """Returns recent command history."""
        try:
            cursor = self._get_conn().cursor()
            cursor.execute("""
                SELECT timestamp, query, agent, tool, rating, success 
                FROM command_history ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            return [
                {"timestamp": r[0], "query": r[1], "agent": r[2], 
                 "tool": r[3], "rating": r[4], "success": r[5]}
                for r in cursor.fetchall()
            ]
        except Exception:
            return []
    
    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


# Singleton
feedback_manager = FeedbackManager()
