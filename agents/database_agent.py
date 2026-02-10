import re
import sqlite3
import shutil
from agents.base_agent import LIAAgent
from core.logger import logger
from core.errors import LIAResult, ErrorCode, ErrorSeverity

class DatabaseAgent(LIAAgent):
    def __init__(self):
        super().__init__("DatabaseAgent", ["SQL queries", "Database backups", "Schema inspection"])
        
        self.register_tool("query_sqlite", self.query_sqlite, "Executes a SELECT query on SQLite",
            keywords=["query", "select", "sql", "table"])
        self.register_tool("backup_db", self.backup_db, "Creates a database backup",
            keywords=["backup", "copy db", "save database"])
        self.register_tool("list_tables", self.list_tables, "Lists all tables in a SQLite database",
            keywords=["tables", "schema", "show tables"])
        self.register_tool("table_info", self.table_info, "Shows columns and types of a table",
            keywords=["columns", "describe", "structure", "fields"])

    def query_sqlite(self, db_path: str, query: str) -> str:
        # SAFETY: Only SELECT allowed
        clean_query = query.strip().upper()
        if not clean_query.startswith("SELECT"):
            return str(LIAResult.fail(ErrorCode.WRITE_NOT_ALLOWED,
                f"Only SELECT queries allowed. Got: {query[:50]}",
                severity=ErrorSeverity.HIGH))
        
        # Block dangerous patterns even in SELECT
        dangerous = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "EXEC", ";"]
        for d in dangerous:
            if d in clean_query and d != ";":
                return str(LIAResult.fail(ErrorCode.WRITE_NOT_ALLOWED,
                    f"Blocked dangerous keyword '{d}' in query"))
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                return "No results."
            
            # Format as aligned table
            col_widths = [max(len(str(col)), max(len(str(row[i])) for row in results[:50]))
                          for i, col in enumerate(columns)]
            
            header = " | ".join(col.ljust(col_widths[i]) for i, col in enumerate(columns))
            separator = "─┼─".join("─" * w for w in col_widths)
            rows = "\n".join(
                " | ".join(str(v).ljust(col_widths[i]) for i, v in enumerate(row))
                for row in results[:50]
            )
            
            output = f"{header}\n{separator}\n{rows}"
            if len(results) > 50:
                output += f"\n... ({len(results)} total, showing first 50)"
            return output
            
        except sqlite3.OperationalError as e:
            return str(LIAResult.fail(ErrorCode.AGENT_CRASHED, f"SQL Error: {str(e)}"))
        except FileNotFoundError:
            return str(LIAResult.fail(ErrorCode.FILE_NOT_FOUND, f"Database not found: {db_path}"))
        except Exception as e:
            return str(LIAResult.fail(ErrorCode.AGENT_CRASHED, str(e)))

    def backup_db(self, db_path: str, backup_path: str = "") -> str:
        if not backup_path:
            import time
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            backup_path = f"{db_path}.backup_{timestamp}"
        try:
            shutil.copy2(db_path, backup_path)
            return f"✅ Backup created: {backup_path}"
        except FileNotFoundError:
            return str(LIAResult.fail(ErrorCode.FILE_NOT_FOUND, f"Database not found: {db_path}"))
        except Exception as e:
            return str(LIAResult.fail(ErrorCode.AGENT_CRASHED, str(e)))

    def list_tables(self, db_path: str = "memory/audit_log.db") -> str:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name")
            items = cursor.fetchall()
            conn.close()
            if not items:
                return "No tables found."
            return "\n".join([f"  {'📊' if t == 'table' else '👁'} {name}" for name, t in items])
        except Exception as e:
            return str(LIAResult.fail(ErrorCode.AGENT_CRASHED, str(e)))

    def table_info(self, db_path: str, table_name: str) -> str:
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            row_count = cursor.fetchone()[0]
            conn.close()
            
            if not columns:
                return f"Table '{table_name}' not found."
            
            lines = [f"Table: {table_name} ({row_count} rows)", "─" * 40]
            for col in columns:
                nullable = "" if col[3] else " (nullable)"
                pk = " 🔑" if col[5] else ""
                lines.append(f"  {col[1]:<20} {col[2]:<10}{pk}{nullable}")
            return "\n".join(lines)
        except Exception as e:
            return str(LIAResult.fail(ErrorCode.AGENT_CRASHED, str(e)))

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        if tool_name == "list_tables":
            match = re.search(r'(?:in|at|for|from)\s+(\S+\.db\S*)', task, re.I)
            return {"db_path": match.group(1) if match else "memory/audit_log.db"}
        if tool_name == "backup_db":
            match = re.search(r'(?:backup|copy)\s+(?:database\s+)?(?:at\s+)?(\S+\.db\S*)', task, re.I)
            return {"db_path": match.group(1) if match else "memory/audit_log.db"}
        if tool_name == "table_info":
            match = re.search(r'(?:describe|info|columns|structure)\s+(?:of\s+)?(\w+)', task, re.I)
            return {
                "db_path": "memory/audit_log.db",
                "table_name": match.group(1) if match else "audit_logs"
            }
        return {}

    def execute(self, task: str) -> str:
        logger.info(f"DatabaseAgent executing: {task}")
        return self.smart_execute(task)
