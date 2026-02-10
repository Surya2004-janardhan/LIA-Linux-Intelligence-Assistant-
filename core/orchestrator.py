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
        try:
            if not user_query or not user_query.strip():
                return {"error": "Empty query provided", "steps": []}
            
            logger.info(f"Generating plan for query: {user_query}")
            
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "user", "content": f"User Request: {user_query}\n\nGenerate the plan JSON:"}
            ]
            
            response_text = llm_bridge.generate(messages, response_format={"type": "json_object"})
            
            if not response_text:
                return {"error": "LLM returned empty response", "steps": []}
            
            # Check for LLM errors
            if "Error" in response_text and "connecting to LLM" in response_text:
                return {"error": response_text, "steps": []}
            
            # Clean response if LLM adds backticks
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            
            plan = json.loads(json_str)
            
            # Validate plan structure
            if not isinstance(plan, dict):
                return {"error": "Plan is not a valid JSON object", "steps": []}
            
            if "steps" not in plan:
                return {"error": "Plan missing 'steps' field", "steps": []}
            
            logger.info(f"Plan generated: {plan.get('plan_name', 'Unnamed')}")
            return plan
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse plan JSON: {e}")
            return {"error": f"Invalid JSON from LLM: {str(e)}", "steps": []}
        except Exception as e:
            logger.error(f"Planning error: {e}")
            return {"error": f"Unexpected error: {str(e)}", "steps": []}

    def run(self, user_query: str):
        """
        Executes the full plan with comprehensive error handling.
        """
        try:
            plan = self.plan(user_query)
            
            # Check for planning errors
            if "error" in plan:
                logger.error(f"Cannot execute - planning failed: {plan['error']}")
                return [{"step": 0, "result": f"Planning Error: {plan['error']}"}]
            
            results = []
            
            for step in plan.get("steps", []):
                agent_name = step.get("agent")
                task = step.get("task")
                
                if not agent_name or not task:
                    error_msg = f"Invalid step {step.get('id', '?')}: missing agent or task"
                    logger.error(error_msg)
                    results.append({"step": step.get('id', '?'), "result": f"Error: {error_msg}"})
                    continue
                
                if agent_name in self.agents:
                    try:
                        logger.info(f"Executing Step {step['id']}: [{agent_name}] -> {task}")
                        agent = self.agents[agent_name]
                        result = agent.execute(task)
                        
                        # Audit Log
                        audit_manager.log_action(agent_name, task, result)
                        
                        results.append({"step": step['id'], "result": result})
                    except Exception as e:
                        error_msg = f"Agent {agent_name} crashed: {str(e)}"
                        logger.error(error_msg)
                        results.append({"step": step['id'], "result": f"Error: {error_msg}"})
                else:
                    error_msg = f"Agent {agent_name} not found (available: {', '.join(self.agents.keys())})"
                    logger.warning(error_msg)
                    results.append({"step": step['id'], "result": f"Error: {error_msg}"})
            
            return results
            
        except Exception as e:
            logger.error(f"Orchestrator run failed: {e}")
            return [{"step": 0, "result": f"Fatal Error: {str(e)}"}]

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
