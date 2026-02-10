from agents.base_agent import LIAAgent
from core.logger import logger
import re

class DatabaseAgent(LIAAgent):
    def __init__(self):
        super().__init__("DatabaseAgent", ["SQL queries", "Database backups", "Schema inspection"])
        
        self.register_tool("query_sqlite", self.query_sqlite, "Executes a SELECT query on SQLite",
            keywords=["query", "select", "sql", "table"])
        self.register_tool("backup_db", self.backup_db, "Creates a database backup",
            keywords=["backup", "copy db", "save database"])
        self.register_tool("list_tables", self.list_tables, "Lists all tables in a SQLite database",
            keywords=["tables", "schema", "show tables"])

    def query_sqlite(self, db_path: str, query: str):
        try:
            import sqlite3
            if not query.strip().upper().startswith("SELECT"):
                return "Safety: Only SELECT queries are allowed. Use the GUI for write operations."
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            results = cursor.fetchall()
            conn.close()
            if not results:
                return "No results."
            # Format as readable table
            header = " | ".join(columns)
            rows = "\n".join([" | ".join(str(v) for v in row) for row in results[:50]])
            return f"{header}\n{'─' * len(header)}\n{rows}"
        except Exception as e:
            return f"SQLite Error: {str(e)}"

    def backup_db(self, db_path: str, backup_path: str = ""):
        try:
            import shutil
            if not backup_path:
                backup_path = db_path + ".backup"
            shutil.copy2(db_path, backup_path)
            return f"Backup created: {backup_path}"
        except FileNotFoundError:
            return f"Database not found: {db_path}"
        except Exception as e:
            return f"Backup Error: {str(e)}"

    def list_tables(self, db_path: str):
        try:
            import sqlite3
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            return "\n".join(tables) if tables else "No tables found."
        except Exception as e:
            return f"Error: {str(e)}"

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        if tool_name == "list_tables":
            match = re.search(r'(?:in|at|for|from)\s+(\S+\.db\S*)', task, re.I)
            return {"db_path": match.group(1) if match else "memory/audit_log.db"}
        if tool_name == "backup_db":
            match = re.search(r'(?:backup|copy)\s+(?:database\s+)?(?:at\s+)?(\S+\.db\S*)', task, re.I)
            return {"db_path": match.group(1) if match else "memory/audit_log.db"}
        return {}

    def execute(self, task: str) -> str:
        logger.info(f"DatabaseAgent executing task: {task}")
        return self.smart_execute(task)
