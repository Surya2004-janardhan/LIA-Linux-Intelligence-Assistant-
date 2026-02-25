import subprocess
import os
import shutil
import platform
from core.logger import logger
from core.config import config

class Sandbox:
    """
    Sandboxing wrapper for WIA commands.
    Provides isolation for high-risk or untrusted tasks.
    Currently focuses on Windows (WIA) but retains Linux compatibility.
    """
    def __init__(self):
        self.enabled = config.get('security.sandbox_enabled', True)
        self.os_type = platform.system().lower()
        self.firejail_path = shutil.which("firejail")
        self.firejail_available = (self.os_type == 'linux' and self.firejail_path is not None)

        if self.enabled and self.firejail_available:
            logger.info("Sandbox Ring initialized using Firejail (Linux).")
        elif self.enabled and self.os_type == 'windows':
            # Placeholder for Windows Sandbox or Job Objects
            logger.info("Sandbox Ring initialized for Windows (Mode: Native Placeholder/AppContainer).")
        elif self.enabled:
            logger.info("Sandbox requested but not supported on this platform.")

    def wrap_command(self, cmd_list: list, network: bool = False, private: bool = True) -> list:
        """
        Wraps a command with isolation if enabled and available.
        """
        if not self.enabled:
            return cmd_list
            
        if self.firejail_available:
            sandbox_args = [self.firejail_path, '--quiet']
            if not network: sandbox_args.append('--net=none')
            if private: sandbox_args.append('--private')
            sandbox_args.append('--noprofile')
            sandbox_args.append('--')
            logger.info(f"Sandboxing command (Linux/Firejail): {' '.join(cmd_list)}")
            return sandbox_args + cmd_list
            
        if self.os_type == 'windows':
            # In the future, we can wrap with 'windows-sandbox.exe' or 'powershell Start-Process -NoNewWindow -Credential ...'
            # For now, we return as-is but log the intent
            if not network:
                logger.debug("Windows Sandbox: Intent to block network for this command (Not yet enforced).")
            return cmd_list

        return cmd_list

# Singleton instance
sandbox = Sandbox()
