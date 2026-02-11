import subprocess
import os
import shutil
import platform
from core.logger import logger
from core.config import config

class Sandbox:
    """
    Sandboxing wrapper using Firejail for Linux commands.
    Provides isolation for high-risk or untrusted tasks.
    """
    def __init__(self):
        self.enabled = config.get('security.sandbox_enabled', True)
        self.os_type = platform.system().lower()
        self.firejail_path = shutil.which("firejail")
        self.firejail_available = (self.os_type == 'linux' and self.firejail_path is not None)

        if self.enabled and not self.firejail_available:
            if self.os_type == 'linux':
                logger.warning("Sandbox enabled but 'firejail' not found in PATH.")
            else:
                logger.info("Sandbox requested but not supported on non-Linux systems.")
        elif self.enabled:
            logger.info("Sandbox Ring initialized using Firejail.")

    def wrap_command(self, cmd_list: list, network: bool = False, private: bool = True) -> list:
        """
        Wraps a command with firejail if enabled and available.
        - network: Allow internet access (default: False)
        - private: Use ephemeral home directory (default: True)
        """
        if not (self.enabled and self.firejail_available):
            return cmd_list
        
        sandbox_args = [self.firejail_path, '--quiet']
        
        if not network:
            sandbox_args.append('--net=none')
        
        if private:
            sandbox_args.append('--private')
            
        # Add basic noprofile for minimal interference, or custom LIA profile later
        sandbox_args.append('--noprofile')
        
        # Terminator for firejail args
        sandbox_args.append('--')
        
        logger.info(f"Sandboxing command: {' '.join(cmd_list)}")
        return sandbox_args + cmd_list

# Singleton instance
sandbox = Sandbox()
