import psutil
import subprocess
import os
from agents.base_agent import LIAAgent
from core.logger import logger
from core.llm_bridge import llm_bridge

class SysAgent(LIAAgent):
    def __init__(self):
        super().__init__("SysAgent", ["Process management", "Service control", "Health monitoring", "Disk status"])
        self.register_tool("check_cpu", self.check_cpu, "Returns current CPU usage percentage")
        self.register_tool("check_ram", self.check_ram, "Returns current RAM usage")
        self.register_tool("check_disk", self.check_disk, "Returns disk usage for all partitions")
        self.register_tool("manage_service", self.manage_service, "Starts, stops, or checks status of a system service (Linux only)")

    def check_cpu(self):
        usage = psutil.cpu_percent(interval=1)
        return f"CPU Usage: {usage}%"

    def check_ram(self):
        ram = psutil.virtual_memory()
        return f"RAM Usage: {ram.percent}% ({ram.used // (1024**2)}MB used / {ram.total // (1024**2)}MB total)"

    def check_disk(self):
        disk = psutil.disk_usage('/')
        return f"Disk Usage (/): {disk.percent}% free of {disk.total // (1024**3)}GB"

    def manage_service(self, service_name: str, action: str):
        """
        Executes systemctl commands. Note: Only works on Linux.
        """
        if os.name == 'nt':
            return "Error: Service management via systemctl is only supported on Linux."
        
        try:
            result = subprocess.run(['systemctl', action, service_name], capture_output=True, text=True)
            if result.returncode == 0:
                return f"Successfully executed '{action}' on '{service_name}'\n{result.stdout}"
            else:
                return f"Failed to execute '{action}' on '{service_name}': {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

    def execute(self, task: str) -> str:
        logger.info(f"SysAgent executing task: {task}")
        
        prompt = f"""
        {self.get_capabilities_prompt()}
        
        User Task: {task}
        
        Decide which tool to use and provide the arguments in JSON format.
        Example: {{"tool": "check_cpu", "args": {{}}}}
        """
        
        messages = [{"role": "system", "content": "You are a specialized System Administration Agent."},
                    {"role": "user", "content": prompt}]
        
        try:
            response = llm_bridge.generate(messages, response_format={"type": "json_object"})
            import json
            data = json.loads(response)
            tool_name = data.get("tool")
            args = data.get("args", {})
            
            if tool_name in self.tools:
                logger.info(f"SysAgent calling tool: {tool_name} with {args}")
                result = self.tools[tool_name]["func"](**args)
                return result
            else:
                return f"Error: Tool {tool_name} not found."
        except Exception as e:
            logger.error(f"SysAgent failed to process task: {e}")
            return f"Task failed: {str(e)}"
