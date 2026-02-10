from agents.base_agent import LIAAgent
from core.logger import logger
from core.llm_bridge import llm_bridge
import subprocess
import os

class PackageAgent(LIAAgent):
    """
    Agent for system package management (apt, yum, pip, npm).
    """
    def __init__(self):
        super().__init__("PackageAgent", ["Package installation", "Updates", "Dependency management"])
        self.register_tool("install_pip", self.install_pip, "Installs a Python package via pip")
        self.register_tool("install_npm", self.install_npm, "Installs a Node package via npm")
        self.register_tool("update_system", self.update_system, "Updates system packages (apt/yum)")

    def install_pip(self, package_name: str):
        try:
            result = subprocess.run(["pip", "install", package_name], capture_output=True, text=True)
            return f"Installed {package_name}" if result.returncode == 0 else f"Error: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

    def install_npm(self, package_name: str):
        try:
            result = subprocess.run(["npm", "install", "-g", package_name], capture_output=True, text=True)
            return f"Installed {package_name}" if result.returncode == 0 else f"Error: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

    def update_system(self):
        if os.name == 'nt':
            return "System updates via package manager not supported on Windows."
        try:
            # Try apt first (Debian/Ubuntu)
            result = subprocess.run(["sudo", "apt", "update"], capture_output=True, text=True)
            if result.returncode == 0:
                return "System packages updated (apt)"
            # Fallback to yum (RedHat/CentOS)
            result = subprocess.run(["sudo", "yum", "update", "-y"], capture_output=True, text=True)
            return "System packages updated (yum)" if result.returncode == 0 else f"Error: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

    def execute(self, task: str) -> str:
        logger.info(f"PackageAgent processing: {task}")
        prompt = f"{self.get_capabilities_prompt()}\n\nTask: {task}\n\nJSON output:"
        messages = [{"role": "system", "content": "You manage software packages."}, {"role": "user", "content": prompt}]
        
        try:
            import json
            response = llm_bridge.generate(messages, response_format={"type": "json_object"})
            data = json.loads(response)
            tool_name = data.get("tool")
            args = data.get("args", {})
            
            if tool_name in self.tools:
                return self.tools[tool_name]["func"](**args)
            return f"Error: Tool {tool_name} not found."
        except Exception as e:
            return f"PackageAgent error: {str(e)}"
