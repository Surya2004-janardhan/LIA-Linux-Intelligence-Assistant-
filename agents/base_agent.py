from abc import ABC, abstractmethod
from typing import List, Dict, Any
from core.logger import logger
import json
import re

class LIAAgent(ABC):
    """
    Base class for all LIA agents.
    
    KEY DESIGN: Smart Routing
    - Uses keyword/regex matching FIRST (zero tokens, instant)
    - Falls back to LLM only for ambiguous tasks
    - This saves ~500 tokens per agent call
    """
    def __init__(self, name: str, capabilities: List[str]):
        self.name = name
        self.capabilities = capabilities
        self.tools = {}
        self.tool_patterns = {}  # keyword -> tool_name mapping

    def register_tool(self, tool_name: str, func, description: str, keywords: List[str] = None):
        """
        Registers a tool with optional keyword patterns for fast routing.
        Keywords allow the agent to skip the LLM call for obvious tasks.
        """
        self.tools[tool_name] = {
            "func": func,
            "description": description
        }
        # Register keyword patterns for zero-token matching
        if keywords:
            for kw in keywords:
                self.tool_patterns[kw.lower()] = tool_name
        logger.info(f"Agent [{self.name}] registered tool: {tool_name}")

    def match_tool_by_keywords(self, task: str) -> tuple:
        """
        Attempts to match a tool using keyword patterns.
        Returns (tool_name, confidence) or (None, 0).
        This is the OS-layer optimization — no LLM needed for obvious tasks.
        """
        task_lower = task.lower()
        
        for keyword, tool_name in self.tool_patterns.items():
            if keyword in task_lower:
                return tool_name, 0.9
        
        return None, 0.0

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        """
        Tries to extract arguments from the task string using simple parsing.
        Override in subclasses for agent-specific extraction logic.
        """
        return {}

    @abstractmethod
    def execute(self, task: str) -> str:
        """Main execution loop for the agent to complete a specific task."""
        pass

    def smart_execute(self, task: str) -> str:
        """
        Two-tier execution:
        1. Fast path: keyword match + regex arg extraction (0 tokens)
        2. Slow path: LLM-based tool selection (500+ tokens)
        """
        # TIER 1: Try keyword matching first (FREE — no LLM call)
        tool_name, confidence = self.match_tool_by_keywords(task)
        
        if tool_name and confidence >= 0.8:
            args = self.extract_args_from_task(task, tool_name)
            logger.info(f"[{self.name}] FAST PATH: {tool_name} (confidence: {confidence}, 0 tokens)")
            try:
                return self.tools[tool_name]["func"](**args)
            except TypeError as e:
                # Args extraction failed, fall through to LLM
                logger.info(f"[{self.name}] Fast path args failed, falling back to LLM: {e}")
        
        # TIER 2: Fall back to LLM (costs tokens but handles ambiguity)
        return self._llm_execute(task)

    def _llm_execute(self, task: str) -> str:
        """LLM-based tool selection. Only used when keyword matching fails."""
        from core.llm_bridge import llm_bridge
        
        # Compact prompt — saves tokens vs the verbose old format
        tools_compact = ", ".join([f"{n}({info['description']})" for n, info in self.tools.items()])
        prompt = f"Tools: {tools_compact}\nTask: {task}\nReturn JSON: {{\"tool\": \"name\", \"args\": {{}}}}"
        
        messages = [
            {"role": "system", "content": f"You are {self.name}. Pick the right tool. JSON only."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = llm_bridge.generate(messages, response_format={"type": "json_object"})
            data = json.loads(response)
            tool_name = data.get("tool")
            args = data.get("args", {})
            
            if tool_name in self.tools:
                logger.info(f"[{self.name}] LLM PATH: {tool_name} with {args}")
                return self.tools[tool_name]["func"](**args)
            return f"Error: Tool {tool_name} not found in {self.name}."
        except Exception as e:
            logger.error(f"[{self.name}] LLM execution failed: {e}")
            return f"Task failed: {str(e)}"

    def get_capabilities_prompt(self) -> str:
        """Returns a COMPACT summary of what this agent can do (saves tokens in orchestrator)."""
        tools_desc = ", ".join([f"{name}" for name in self.tools.keys()])
        return f"{self.name}: {', '.join(self.capabilities)} | Tools: {tools_desc}"
