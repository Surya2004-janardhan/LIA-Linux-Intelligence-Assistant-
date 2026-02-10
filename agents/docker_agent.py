from agents.base_agent import LIAAgent
from core.logger import logger
from core.llm_bridge import llm_bridge
import subprocess
import os

class DockerAgent(LIAAgent):
    """
    Agent for Docker container management and orchestration.
    """
    def __init__(self):
        super().__init__("DockerAgent", ["Container management", "Image operations", "Docker Compose"])
        self.register_tool("list_containers", self.list_containers, "Lists running Docker containers")
        self.register_tool("start_container", self.start_container, "Starts a Docker container")
        self.register_tool("stop_container", self.stop_container, "Stops a Docker container")
        self.register_tool("compose_up", self.compose_up, "Runs docker-compose up")

    def list_containers(self):
        try:
            result = subprocess.run(["docker", "ps", "-a"], capture_output=True, text=True)
            return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
        except Exception as e:
            return f"Docker not installed or error: {str(e)}"

    def start_container(self, container_name: str):
        try:
            result = subprocess.run(["docker", "start", container_name], capture_output=True, text=True)
            return f"Started {container_name}" if result.returncode == 0 else f"Error: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

    def stop_container(self, container_name: str):
        try:
            result = subprocess.run(["docker", "stop", container_name], capture_output=True, text=True)
            return f"Stopped {container_name}" if result.returncode == 0 else f"Error: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

    def compose_up(self, path: str = "."):
        try:
            result = subprocess.run(["docker-compose", "up", "-d"], cwd=path, capture_output=True, text=True)
            return "Compose started" if result.returncode == 0 else f"Error: {result.stderr}"
        except Exception as e:
            return f"Error: {str(e)}"

    def execute(self, task: str) -> str:
        logger.info(f"DockerAgent processing: {task}")
        prompt = f"{self.get_capabilities_prompt()}\n\nTask: {task}\n\nJSON output:"
        messages = [{"role": "system", "content": "You manage Docker containers."}, {"role": "user", "content": prompt}]
        
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
            return f"DockerAgent error: {str(e)}"
