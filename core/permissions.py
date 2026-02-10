"""
LIA Permission Manager v2 — Production-grade access control.

Features:
1. Path whitelisting/blacklisting with symlink resolution
2. Per-agent permission scoping (FileAgent can access X, GitAgent can access Y)
3. Operation-level permissions (read, write, execute, delete)
4. Connection kill-switches with audit logging
5. Permission caching for performance
"""
import os
from typing import List, Dict, Set
from enum import Enum, auto
from core.config import config
from core.logger import logger


class Operation(Enum):
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    DELETE = auto()


class PermissionManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # Path rules
        self.allowed_paths = [
            os.path.realpath(os.path.abspath(os.path.expanduser(p)))
            for p in config.get('permissions.allowed_paths', [
                "~/Documents", "~/Downloads", "~/Desktop", "."
            ])
        ]
        
        # System paths that are ALWAYS blocked (hardcoded, not configurable)
        self.blocked_paths = self._get_system_blocked_paths()
        
        # Per-agent restrictions: agent_name -> set of allowed operations
        self.agent_permissions: Dict[str, Set[Operation]] = {
            "FileAgent": {Operation.READ, Operation.WRITE, Operation.EXECUTE},
            "SysAgent": {Operation.READ, Operation.EXECUTE},
            "GitAgent": {Operation.READ, Operation.WRITE, Operation.EXECUTE},
            "NetAgent": {Operation.EXECUTE},
            "WebAgent": {Operation.EXECUTE},
            "ConnectionAgent": {Operation.READ, Operation.EXECUTE},
            "DockerAgent": {Operation.EXECUTE},
            "DatabaseAgent": {Operation.READ},  # SELECT only
            "PackageAgent": {Operation.EXECUTE},
        }
        
        # Connection toggles
        self.connections = {
            "gmail": config.get('connections.gmail_enabled', False),
            "calendar": config.get('connections.calendar_enabled', False),
            "custom_api": config.get('connections.custom_api_enabled', False)
        }
        
        # Permission check cache (path -> result)
        self._cache: Dict[str, bool] = {}
        
        logger.info(f"PermissionManager: {len(self.allowed_paths)} allowed paths, "
                     f"{len(self.blocked_paths)} blocked paths")

    def _get_system_blocked_paths(self) -> List[str]:
        """Returns OS-specific system paths that should never be accessible."""
        blocked = []
        if os.name == 'nt':
            blocked.extend([
                os.path.realpath("C:\\Windows"),
                os.path.realpath("C:\\Windows\\System32"),
                os.path.realpath("C:\\Program Files"),
                os.path.realpath("C:\\Program Files (x86)"),
                os.path.realpath(os.path.expanduser("~\\AppData\\Local\\Microsoft")),
            ])
        else:
            blocked.extend([
                "/etc", "/boot", "/root", "/var/log", "/usr/sbin",
                "/proc", "/sys", "/dev"
            ])
        return blocked

    def is_path_allowed(self, path: str, operation: Operation = Operation.READ) -> bool:
        """
        Checks if a path is accessible.
        Resolves symlinks to prevent traversal attacks.
        """
        # Resolve symlinks, .., and ~ BEFORE checking
        try:
            abs_path = os.path.realpath(os.path.abspath(os.path.expanduser(path)))
        except (OSError, ValueError):
            logger.warning(f"PERMISSION DENIED: Invalid path: {path}")
            return False
        
        # Check cache
        cache_key = f"{abs_path}:{operation.name}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Check blocked paths first (always deny)
        for blocked in self.blocked_paths:
            if abs_path.startswith(blocked):
                logger.warning(f"BLOCKED: {abs_path} (matches system path {blocked})")
                self._cache[cache_key] = False
                return False
        
        # Check allowed paths
        allowed = False
        for allowed_path in self.allowed_paths:
            if abs_path.startswith(allowed_path):
                allowed = True
                break
        
        if not allowed:
            logger.warning(f"DENIED: {abs_path} not in allowed paths")
        
        self._cache[cache_key] = allowed
        return allowed

    def check_agent_operation(self, agent_name: str, operation: Operation) -> bool:
        """Checks if a specific agent is allowed to perform an operation type."""
        allowed_ops = self.agent_permissions.get(agent_name, set())
        if operation not in allowed_ops:
            logger.warning(f"DENIED: {agent_name} cannot perform {operation.name}")
            return False
        return True

    def is_connection_active(self, connection_name: str) -> bool:
        """Checks if a 3rd party connection is enabled."""
        active = self.connections.get(connection_name, False)
        if not active:
            logger.info(f"Connection '{connection_name}' is disabled.")
        return active

    def enable_connection(self, connection_name: str):
        """Enables a connection at runtime (also saves to config)."""
        self.connections[connection_name] = True
        config.set(f'connections.{connection_name}_enabled', True)
        logger.info(f"Connection enabled: {connection_name}")

    def disable_connection(self, connection_name: str):
        """Disables a connection at runtime."""
        self.connections[connection_name] = False
        config.set(f'connections.{connection_name}_enabled', False)
        logger.info(f"Connection disabled: {connection_name}")

    def add_allowed_path(self, path: str):
        """Adds a path to the whitelist at runtime."""
        resolved = os.path.realpath(os.path.abspath(os.path.expanduser(path)))
        if resolved not in self.allowed_paths:
            self.allowed_paths.append(resolved)
            self._cache.clear()  # Invalidate cache
            # Update config
            current = config.get('permissions.allowed_paths', [])
            current.append(path)
            config.set('permissions.allowed_paths', current)
            logger.info(f"Path whitelisted: {resolved}")

    def clear_cache(self):
        """Clears the permission cache (e.g., after config reload)."""
        self._cache.clear()

    def get_status(self) -> dict:
        """Returns current permission state for GUI display."""
        return {
            "allowed_paths": self.allowed_paths,
            "blocked_paths": self.blocked_paths,
            "connections": self.connections,
            "agent_permissions": {
                name: [op.name for op in ops] 
                for name, ops in self.agent_permissions.items()
            }
        }


# Singleton instance
permission_manager = PermissionManager()
