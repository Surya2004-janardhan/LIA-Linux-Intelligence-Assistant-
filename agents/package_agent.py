from agents.base_agent import LIAAgent
from core.logger import logger
import subprocess
import os
import re

class PackageAgent(LIAAgent):
    def __init__(self):
        super().__init__("PackageAgent", ["Package installation", "Updates", "Dependency management"])
        
        self.register_tool("install_pip", self.install_pip, "Installs a Python package via pip",
            keywords=["pip install", "python package", "pip"])
        self.register_tool("install_npm", self.install_npm, "Installs a Node package via npm",
            keywords=["npm install", "node package", "npm"])
        self.register_tool("list_pip", self.list_pip, "Lists installed pip packages",
            keywords=["pip list", "installed packages", "python packages"])
        self.register_tool("update_system", self.update_system, "Updates system packages",
            keywords=["update system", "apt update", "system update"])

    def _run(self, cmd: list, timeout: int = 60):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
        except FileNotFoundError:
            return f"'{cmd[0]}' not found. Is it installed?"
        except subprocess.TimeoutExpired:
            return f"Timeout: {' '.join(cmd)}"
        except Exception as e:
            return f"Error: {str(e)}"

    def install_pip(self, package_name: str):
        return self._run(["pip", "install", package_name])

    def install_npm(self, package_name: str):
        return self._run(["npm", "install", "-g", package_name])

    def list_pip(self):
        return self._run(["pip", "list", "--format=columns"])

    def update_system(self):
        if os.name == 'nt':
            return "System package updates not supported on Windows via CLI."
        return self._run(["sudo", "apt", "update"], timeout=120)

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        if tool_name in ("install_pip", "install_npm"):
            match = re.search(r'install\s+(\S+)', task, re.I)
            return {"package_name": match.group(1) if match else ""}
        return {}

    def execute(self, task: str) -> str:
        logger.info(f"PackageAgent executing task: {task}")
        return self.smart_execute(task)
