import subprocess
import os
from agents.base_agent import LIAAgent
from core.logger import logger
from core.llm_bridge import llm_bridge

class NetAgent(LIAAgent):
    def __init__(self):
        super().__init__("NetAgent", ["Network diagnostics", "Speed test", "Ping", "Port scanning"])
        self.register_tool("ping_host", self.ping_host, "Pings a host to check connectivity")
        self.register_tool("check_ports", self.check_ports, "Scans local ports (Linux nmap recommended)")

    def ping_host(self, host: str):
        # Use -n for Windows, -c for Linux
        param = '-n' if os.name == 'nt' else '-c'
        try:
            result = subprocess.run(['ping', param, '4', host], capture_output=True, text=True)
            return result.stdout if result.returncode == 0 else f"Ping failed: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

    def check_ports(self, target: str = "localhost"):
        try:
            # Requires nmap to be installed
            result = subprocess.run(['nmap', target], capture_output=True, text=True)
            return result.stdout if result.returncode == 0 else f"Nmap fail (is it installed?): {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

    def execute(self, task: str) -> str:
        logger.info(f"NetAgent executing task: {task}")
        prompt = f"{self.get_capabilities_prompt()}\n\nUser Task: {task}\n\nDecide tool and args in JSON:"
        messages = [{"role": "system", "content": "You are a Network administrator agent."}, {"role": "user", "content": prompt}]
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
            return f"NetAgent failed: {str(e)}"
