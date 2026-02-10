import subprocess
import os
from core.logger import logger
from core.config import config

class Sandbox:
    def __init__(self):
        self.enabled = config.get('security.sandbox_enabled', False)
        # Check if firejail is actually installed
        self.firejail_available = self._check_firejail()

    def _check_firejail(self):
        if os.name == 'nt':
            return False
        try:
            subprocess.run(['firejail', '--version'], capture_output=True)
            return True
        except:
            return False

    def wrap_command(self, cmd_list: list) -> list:
        """
        Wraps a command with firejail if enabled and available.
        """
        if self.enabled and self.firejail_available:
            logger.info(f"Sandboxing command: {' '.join(cmd_list)}")
            return ['firejail', '--quiet', '--noprofile'] + cmd_list
        return cmd_list

# Singleton instance
sandbox = Sandbox()
