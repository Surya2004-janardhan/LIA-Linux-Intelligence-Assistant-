"""
LIA Base Agent — Two-Tier Smart Routing (Async).
Tier 1: Keyword match (0 tokens)
Tier 2: LLM fallback (200+ tokens)
Now fully async.
"""
import re
import asyncio
from typing import Dict, Any, Tuple
from core.llm_bridge import llm_bridge
from core.logger import logger
from core.errors import LIAResult, ErrorCode

class LIAAgent:
    def __init__(self, name: str, capabilities: list):
        self.name = name
        self.capabilities = capabilities
        self.tools = {}  # {name: {func, desc, keywords}}
        logger.info(f"Initialized {self.name}")

    def register_tool(self, name: str, func: callable, description: str, keywords: list):
        self.tools[name] = {
            "func": func,
            "desc": description,
            "keywords": [k.lower() for k in keywords]
        }

    def get_capabilities_prompt(self) -> str:
        tools_desc = ", ".join([f"{n} ({t['desc']})" for n, t in self.tools.items()])
        return f"{self.name}: {', '.join(self.capabilities)}. Tools: {tools_desc}"

    def match_tool_by_keywords(self, task: str) -> Tuple[str, float]:
        """Tier 1: Zero-shot keyword matching."""
        task_lower = task.lower()
        best_match = None
        max_score = 0.0
        
        for name, tool in self.tools.items():
            score = 0
            for kw in tool["keywords"]:
                if kw in task_lower:
                    score += 1
            if score > max_score:
                max_score = score
                best_match = name
        
        # Heuristic confidence
        confidence = min(max_score * 0.4, 1.0)
        return best_match, confidence

    async def _llm_execute(self, task: str) -> str:
        """Tier 2: LLM reasoning (expensive fallback)."""
        logger.info(f"[{self.name}] Falling back to LLM for: {task}")
        
        # Construct tools schema
        tools_schema = "\n".join([
            f"- {name}: {t['desc']} (args: inferred from task)" 
            for name, t in self.tools.items()
        ])
        
        prompt = f"""You are {self.name}. Task: "{task}"
Available Tools:
{tools_schema}

Return only the tool name and arguments in JSON format:
{{"tool": "tool_name", "args": {{"arg_name": "value"}}}}
If no tool fits, return {{"error": "reason"}}."""

        response = await asyncio.to_thread(llm_bridge.generate, [{"role": "user", "content": prompt}], {"type": "json_object"})
        
        try:
            import json
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            
            plan = json.loads(response)
            tool_name = plan.get("tool")
            args = plan.get("args", {})
            
            if tool_name in self.tools:
                func = self.tools[tool_name]["func"]
                if asyncio.iscoroutinefunction(func):
                    return await func(**args)
                else:
                    return await asyncio.to_thread(func, **args)
            return f"Error: {plan.get('error', 'Unknown tool')}"
            
        except Exception as e:
            return f"Agent Error: {str(e)}"

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        """
        Regex-based argument extraction (Tier 1).
        Override in subclasses for specific logic.
        """
        return {}

    async def smart_execute(self, task: str) -> str:
        """
        The core logic: Try keywords first, then LLM.
        """
        try:
            # TIER 1: Keyword Match
            tool_name, confidence = self.match_tool_by_keywords(task)
            
            if tool_name and confidence >= 0.8:
                logger.info(f"[{self.name}] Keyword match: {tool_name} ({confidence:.2f})")
                args = self.extract_args_from_task(task, tool_name)
                func = self.tools[tool_name]["func"]
                
                if asyncio.iscoroutinefunction(func):
                    return await func(**args)
                else:
                    # Run sync tool in thread pool to avoid blocking loop
                    return await asyncio.to_thread(func, **args)

            # TIER 2: LLM Fallback
            return await self._llm_execute(task)
            
        except Exception as e:
            logger.error(f"[{self.name}] Crash: {e}")
            return str(LIAResult.fail(ErrorCode.AGENT_CRASHED, str(e)))

    async def execute(self, task: str) -> str:
        """Entry point. Subclasses implement logic or call smart_execute."""
        return await self.smart_execute(task)
