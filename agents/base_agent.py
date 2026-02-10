from abc import ABC, abstractmethod
from typing import List, Dict, Any
from core.logger import logger

class LIAAgent(ABC):
    def __init__(self, name: str, capabilities: List[str]):
        self.name = name
        self.capabilities = capabilities
        self.tools = {}

    def register_tool(self, tool_name: str, func, description: str):
        """
        Registers a tool that this agent can execute.
        """
        self.tools[tool_name] = {
            "func": func,
            "description": description
        }
        logger.info(f"Agent [{self.name}] registered tool: {tool_name}")

    @abstractmethod
    def execute(self, task: str) -> str:
        """
        Main execution loop for the agent to complete a specific task.
        """
        pass

    def get_capabilities_prompt(self) -> str:
        """
        Returns a string summarizing what this agent can do.
        """
        tools_desc = "\n".join([f"- {name}: {info['description']}" for name, info in self.tools.items()])
        return f"Agent: {self.name}\nCapabilities: {', '.join(self.capabilities)}\nTools:\n{tools_desc}"
