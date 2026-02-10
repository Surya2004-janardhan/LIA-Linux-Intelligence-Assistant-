from agents.base_agent import LIAAgent
from core.logger import logger
from core.llm_bridge import llm_bridge
import subprocess

class DatabaseAgent(LIAAgent):
    """
    Agent for database operations (PostgreSQL, MySQL, SQLite).
    """
    def __init__(self):
        super().__init__("DatabaseAgent", ["SQL queries", "Database backups", "Schema inspection"])
        self.register_tool("query_sqlite", self.query_sqlite, "Executes a SELECT query on SQLite database")
        self.register_tool("backup_db", self.backup_db, "Creates a database backup")

    def query_sqlite(self, db_path: str, query: str):
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            conn.close()
            return str(results) if results else "No results."
        except Exception as e:
            return f"SQLite Error: {str(e)}"

    def backup_db(self, db_path: str, backup_path: str):
        try:
            import shutil
            shutil.copy2(db_path, backup_path)
            return f"Backup created: {backup_path}"
        except Exception as e:
            return f"Backup Error: {str(e)}"

    def execute(self, task: str) -> str:
        logger.info(f"DatabaseAgent processing: {task}")
        prompt = f"{self.get_capabilities_prompt()}\n\nTask: {task}\n\nJSON output:"
        messages = [{"role": "system", "content": "You manage databases."}, {"role": "user", "content": prompt}]
        
        try:
            import json
            response = llm_bridge.generate(messages, response_format={"type": "json_object"})
            data = json.loads(response)
            tool_name = data.get("tool")
            args = data.get("args", {})
            
            if tool_name in self.tools:
                return self.tools[tool_name]["func"](**args)
            return f"Error: Tool {tool_name} not found."
        except Exception as e:
            return f"DatabaseAgent error: {str(e)}"
