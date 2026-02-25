"""
WIA Memory Manager — Central Knowledge Base & Setup.

Includes:
- Interactive 'First Run' setup to ask user for allowed system paths.
- FAISS vector storage for long-term memory.
"""
import os
import sys
import json
import sqlite3
import numpy as np
from typing import List, Dict, Optional
from core.logger import logger
from core.config import config
from core.permissions import permission_manager

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not found. Vector memory will be disabled.")


class MemoryManager:
    """
    Manages semantic memory (vector DB) and facts (SQLite).
    Triggers setup wizard if system context is not defined.
    """
    
    def __init__(self, db_path="memory/WIA.db"):
        self.db_path = db_path
        self._index = None
        self._conn = None
        
        # Check permissions immediately
        self._ensure_setup()
        
        if FAISS_AVAILABLE:
            self._init_faiss()
        self._init_sqlite()

    def _ensure_setup(self):
        """
        Interactive Setup Wizard.
        Runs if permissions.allowed_paths is empty or default.
        """
        existing_paths = config.get("permissions.allowed_paths", [])
        
        # If config is pristine, we must ask the user
        if not existing_paths or existing_paths == ["."]:
            print("\n╔═════════════════════════════════════════════════════════════════╗")
            print("║   WIA Initial Setup (First Run)                                 ║")
            print("╠═════════════════════════════════════════════════════════════════╣")
            print("║ To function safely, WIA needs to know which directories         ║")
            print("║ it is allowed to access and embed into memory.                  ║")
            print("║                                                                 ║")
            print("║ Examples:                                                       ║")
            print("║   /home/user/projects                                           ║")
            print("║   /var/www/html                                                 ║")
            print("║   . (current directory only)                                    ║")
            print("╚═════════════════════════════════════════════════════════════════╝")
            
            user_input = input("\nEnter allowed paths (comma separated): ").strip()
            
            new_paths = [p.strip() for p in user_input.split(",") if p.strip()]
            if not new_paths:
                new_paths = ["."]
                print("No paths provided. Defaulting to Current Directory only.")
            
            # Save permissions
            permission_manager.configure_paths(new_paths)
            print(f"✅ Configuration saved. Allowed Context: {new_paths}\n")
            
    def _init_faiss(self):
        try:
            self._index = faiss.IndexFlatL2(384)  # Example dimension for MiniLM
        except Exception as e:
            logger.error(f"FAISS init error: {e}")

    def _init_sqlite(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY,
                category TEXT,
                content TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
    
    def add_fact(self, category: str, content: str):
        self._conn.execute("INSERT INTO facts (category, content) VALUES (?, ?)", 
                          (category, content))
        self._conn.commit()

    def query_facts(self, category: str) -> List[str]:
        cursor = self._conn.execute("SELECT content FROM facts WHERE category = ?", (category,))
        return [row[0] for row in cursor.fetchall()]

    def close(self):
        if self._conn:
            self._conn.close()

# Singleton
central_memory = MemoryManager()
