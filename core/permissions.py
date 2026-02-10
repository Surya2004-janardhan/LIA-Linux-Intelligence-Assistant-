import os
from typing import List
from core.config import config
from core.logger import logger

class PermissionManager:
    """
    Manages granular access control for LIA agents.
    Defines which folders can be read/written and which APIs/Tools are restricted.
    """
    def __init__(self):
        # Default allowed paths (can be customized in config.yaml)
        self.allowed_paths = config.get('permissions.allowed_paths', [
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Desktop"),
            os.getcwd()
        ])
        
        # Blocked system paths
        self.blocked_paths = [
            "/etc", "/boot", "/root", "/var/log",
            "C:\\Windows", "C:\\Users\\Default"
        ]
        
        # Third-party connection status
        self.connections = {
            "gmail": config.get('connections.gmail_enabled', False),
            "calendar": config.get('connections.calendar_enabled', False),
            "custom_api": config.get('connections.custom_api_enabled', False)
        }

    def is_path_allowed(self, path: str) -> bool:
        """
        Checks if the agent has permission to access a specific path.
        """
        abs_path = os.path.abspath(path)
        
        # Check against blocked system paths first
        for blocked in self.blocked_paths:
            if abs_path.startswith(blocked):
                logger.warning(f"PERMISSION DENIED: Agent tried to access blacklisted path: {abs_path}")
                return False
        
        # Check against allowed user paths
        for allowed in self.allowed_paths:
            if abs_path.startswith(os.path.abspath(allowed)):
                return True
        
        logger.warning(f"PERMISSION DENIED: Path not in allowed list: {abs_path}")
        return False

    def is_connection_active(self, connection_name: str) -> bool:
        """Checks if a 3rd party connection (like Gmail) is enabled."""
        return self.connections.get(connection_name, False)

# Singleton instance
permission_manager = PermissionManager()
