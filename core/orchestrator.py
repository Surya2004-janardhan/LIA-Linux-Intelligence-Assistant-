import json
from typing import List, Dict, Any
from core.llm_bridge import llm_bridge
from core.logger import logger
from core.audit import audit_manager
from agents.base_agent import LIAAgent

class Orchestrator:
    def __init__(self, agents: List[LIAAgent]):
        self.agents = {agent.name: agent for agent in agents}
        self.history = []

    def _get_system_prompt(self) -> str:
        agent_descriptions = "\n\n".join([a.get_capabilities_prompt() for a in self.agents.values()])
        return f"""
You are the LIA Orchestrator - a master planner for a swarm of specialized Linux automation agents.

Available Agents:
{agent_descriptions}

Your Mission:
1. Analyze the user's request carefully
2. Break it down into logical, sequential tasks
3. Route each task to the MOST APPROPRIATE agent based on their capabilities
4. Consider dependencies between steps
5. Return a structured JSON plan

Routing Guidelines:
- FileAgent: File operations, directory management, file search
- SysAgent: System monitoring, service management, process control
- GitAgent: Version control, commits, GitHub operations
- NetAgent: Network diagnostics, connectivity checks, port scanning
- WebAgent: Browser automation, web searches, URL opening
- ConnectionAgent: Email, calendar, external APIs (check if enabled)
- DockerAgent: Container management, docker-compose operations
- DatabaseAgent: SQL queries, database backups, schema operations
- PackageAgent: Software installation (pip, npm, apt, yum)

Example JSON Output:
{{
  "plan_name": "descriptive name",
  "steps": [
    {{
      "id": 1,
      "agent": "AgentName",
      "task": "Clear, specific task description"
    }}
  ]
}}

IMPORTANT: Choose the agent that BEST matches the task domain. If uncertain, prefer simpler agents over complex ones.
"""

    def plan(self, user_query: str) -> Dict[str, Any]:
        """
        Uses LLM to generate a structured plan from user query.
        """
        logger.info(f"Generating plan for query: {user_query}")
        
        messages = [
            {"role": "system", "content": self._get_system_prompt()},
            {"role": "user", "content": f"User Request: {user_query}\n\nGenerate the plan JSON:"}
        ]
        
        response_text = llm_bridge.generate(messages, response_format={"type": "json_object"})
        
        try:
            # Clean response if LLM adds backticks
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
                
            plan = json.loads(json_str)
            logger.info(f"Plan generated: {plan.get('plan_name')}")
            return plan
        except Exception as e:
            logger.error(f"Failed to parse plan JSON: {e}")
            return {"error": str(e), "steps": []}

    def run(self, user_query: str):
        """
        Executes the full plan.
        """
        plan = self.plan(user_query)
        results = []
        
        for step in plan.get("steps", []):
            agent_name = step.get("agent")
            task = step.get("task")
            
            if agent_name in self.agents:
                logger.info(f"Executing Step {step['id']}: [{agent_name}] -> {task}")
                agent = self.agents[agent_name]
                result = agent.execute(task)
                
                # Audit Log
                audit_manager.log_action(agent_name, task, result)
                
                results.append({"step": step['id'], "result": result})
            else:
                logger.warning(f"Agent {agent_name} not found for step {step['id']}")
        
        return results

    async def run_async(self, user_query: str):
        """
        Executes the full plan asynchronously (Parallel Swarm).
        Enables concurrent agent execution for faster multi-step workflows.
        """
        import asyncio
        plan = self.plan(user_query)
        tasks = []
        
        for step in plan.get("steps", []):
            agent_name = step.get("agent")
            task_desc = step.get("task")
            
            if agent_name in self.agents:
                logger.info(f"Queuing Parallel Step {step['id']}: [{agent_name}]")
                agent = self.agents[agent_name]
                tasks.append(self._execute_step_async(step, agent))
        
        results = await asyncio.gather(*tasks)
        return results

    async def _execute_step_async(self, step, agent):
        """Helper to execute a single agent step asynchronously."""
        result = agent.execute(step['task'])
        audit_manager.log_action(agent.name, step['task'], result)
        return {"step": step['id'], "result": result}
