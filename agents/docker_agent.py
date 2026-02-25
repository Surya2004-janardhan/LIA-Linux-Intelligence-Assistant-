import re
from agents.base_agent import WIAAgent
from core.logger import logger
from core.os_layer import os_layer
from core.errors import WIAResult, ErrorCode

class DockerAgent(WIAAgent):
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
        self.register_tool("list_images", self.list_images, "Lists Docker images",
            keywords=["images", "docker images"])
        self.register_tool("container_logs", self.container_logs, "Shows container logs",
            keywords=["logs", "docker logs"])

    async def _docker(self, cmd: list, timeout: int = 30) -> str:
        result = await os_layer.run_command(cmd, timeout=timeout)
        if not result["success"]:
            if "not found" in result["stderr"].lower() or result["returncode"] == -1:
                return str(WIAResult.fail(ErrorCode.DEPENDENCY_MISSING,
                    "Docker not found", suggestion="Install Docker: https://docs.docker.com/desktop/install/windows-install/"))
            if result["timed_out"]:
                return str(WIAResult.fail(ErrorCode.COMMAND_TIMEOUT, 
                    f"Docker command timed out after {timeout}s"))
            return str(WIAResult.fail(ErrorCode.AGENT_CRASHED, result["stderr"]))
        return result["stdout"] if result["stdout"] else "Command completed (no output)."

    async def list_containers(self) -> str:
        return await self._docker(["docker", "ps", "-a", "--format", 
            "table {{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"])

    async def start_container(self, container_name: str) -> str:
        result = await self._docker(["docker", "start", container_name])
        if "WIAResult.fail" not in result and "Error" not in result:
            return f"✅ Container started: {container_name}"
        return result

    async def stop_container(self, container_name: str) -> str:
        result = await self._docker(["docker", "stop", container_name], timeout=15)
        if "WIAResult.fail" not in result and "Error" not in result:
            return f"✅ Container stopped: {container_name}"
        return result

    async def compose_up(self, path: str = ".") -> str:
        return await self._docker(["docker-compose", "up", "-d"], timeout=120)

    async def list_images(self) -> str:
        return await self._docker(["docker", "images", "--format", 
            "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"])

    async def container_logs(self, container_name: str, lines: int = 50) -> str:
        return await self._docker(["docker", "logs", "--tail", str(lines), container_name])

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        if tool_name in ("start_container", "stop_container", "container_logs"):
            match = re.search(r'(?:start|stop|logs?\s+(?:of|for)?)\s+(?:container\s+)?(\S+)', task, re.I)
            return {"container_name": match.group(1) if match else ""}
        return {}

    def execute(self, task: str) -> str:
        logger.info(f"DockerAgent executing: {task}")
        return self.smart_execute(task)
