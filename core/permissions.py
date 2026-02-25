"""
WIA Permission Manager — Dynamic Access Control.
No hardcoded paths. Everything is user-defined via config or setup.
"""
import os
import shutil
from typing import List, Dict, Optional
from core.config import config
from core.logger import logger

class PermissionManager:
    """
    Manages filesystem and network permissions.
    Paths are loaded from config.yaml dynamically.
    """
    
    def __init__(self):
        self._allowed_paths: List[str] = []
        self._temp_stack: List[List[str]] = []
        self._cache = {}
        self.reload()

    def reload(self):
        """Reloads permissions from config."""
        paths = config.get("permissions.allowed_paths", [])
        
        # If no paths configured, default to CWD only for safety
        if not paths:
            paths = ["."]
            
        # Resolve all paths
        self._allowed_paths = []
        for p in paths:
            try:
                if p == ".":
                    resolved = os.getcwd()
                else:
                    resolved = os.path.abspath(os.path.expanduser(p))
                self._allowed_paths.append(resolved)
            except Exception as e:
                logger.warning(f"Failed to resolve allowed path '{p}': {e}")
                
        self._cache = {}
        logger.info(f"Permissions loaded. Allowed scopes: {self._allowed_paths}")

    def temporary_scope(self, paths: List[str]):
        """
        Context manager for temporary permission narrowing.
        """
        class TempScope:
            def __init__(self, pm, new_paths):
                self.pm = pm
                self.new_paths = [os.path.abspath(os.path.expanduser(p)) for p in new_paths]
                self.old_paths = None

            def __enter__(self):
                self.old_paths = self.pm._allowed_paths.copy()
                self.pm._allowed_paths = self.new_paths
                self.pm._cache = {}
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.pm._allowed_paths = self.old_paths
                self.pm._cache = {}

        return TempScope(self, paths)

    def is_path_allowed(self, path: str) -> bool:
        """
        Checks if path is within allowed scopes.
        Resolves symlinks to prevent traversal.
        """
        if path in self._cache:
            return self._cache[path]
            
        try:
            # Resolve target path fully
            target = os.path.abspath(os.path.expanduser(path))
            real_target = os.path.realpath(target)
            
            allowed = False
            for parent in self._allowed_paths:
                # Check if target is inside parent (or is parent)
                # We use commonpath to verify
                try:
                    common = os.path.commonpath([parent, real_target])
                    if common == parent:
                        allowed = True
                        break
                except ValueError:
                    continue  # Different drives on Windows
            
            self._cache[path] = allowed
            if not allowed:
                logger.warning(f"Permission DENIED: {path} (not in {self._allowed_paths})")
            return allowed
            
        except Exception as e:
            logger.error(f"Permission check failed for {path}: {e}")
            return False

    def is_connection_active(self, connection_name: str) -> bool:
        return config.get(f"permissions.connections.{connection_name}_enabled", False)

# Singleton
permission_manager = PermissionManager()
