from agents.base_agent import LIAAgent
from core.logger import logger

class MockAgent(LIAAgent):
    def __init__(self, name: str, capabilities: list):
        super().__init__(name, capabilities)
        # Register some fake tools for testing
        self.register_tool("echo", self.echo, "Prints back the input")
        self.register_tool("ping_mock", self.ping, "Mocks a network ping")

    def echo(self, text: str):
        return f"Echo: {text}"

    def ping(self, host: str):
        return f"Mocked ping to {host}: SUCCESS"

    def execute(self, task: str) -> str:
        logger.info(f"MockAgent [{self.name}] processing: {task}")
        # In a real agent, we'd use LLM to pick a tool. 
        # For now, we mock the result.
        return f"Executed: {task} (Result: OK)"
