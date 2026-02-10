from agents.base_agent import LIAAgent
from core.logger import logger
import subprocess

class DockerAgent(LIAAgent):
    def __init__(self):
        super().__init__("DockerAgent", ["Container management", "Image operations", "Docker Compose"])
        
        self.register_tool("list_containers", self.list_containers, "Lists Docker containers",
            keywords=["list container", "docker ps", "containers", "running container"])
        self.register_tool("start_container", self.start_container, "Starts a Docker container",
            keywords=["start container", "docker start"])
        self.register_tool("stop_container", self.stop_container, "Stops a Docker container",
            keywords=["stop container", "docker stop"])
        self.register_tool("compose_up", self.compose_up, "Runs docker-compose up",
            keywords=["compose", "docker-compose", "compose up"])

    def _docker_cmd(self, cmd: list, timeout: int = 30):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
        except FileNotFoundError:
            return "Docker not found. Is Docker installed and in PATH?"
        except subprocess.TimeoutExpired:
            return f"Timeout: {' '.join(cmd)}"
        except Exception as e:
            return f"Error: {str(e)}"

    def list_containers(self):
        return self._docker_cmd(["docker", "ps", "-a", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"])

    def start_container(self, container_name: str):
        return self._docker_cmd(["docker", "start", container_name])

    def stop_container(self, container_name: str):
        return self._docker_cmd(["docker", "stop", container_name])

    def compose_up(self, path: str = "."):
        return self._docker_cmd(["docker-compose", "up", "-d"], timeout=60)

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        import re
        if tool_name in ("start_container", "stop_container"):
            match = re.search(r'(?:start|stop)\s+(?:container\s+)?(\S+)', task, re.I)
            return {"container_name": match.group(1) if match else ""}
        return {}

    def execute(self, task: str) -> str:
        logger.info(f"DockerAgent executing task: {task}")
        return self.smart_execute(task)
