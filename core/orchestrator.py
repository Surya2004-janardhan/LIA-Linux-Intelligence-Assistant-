import json
from typing import List, Dict, Any
from core.llm_bridge import llm_bridge
from core.logger import logger
from agents.base_agent import LIAAgent

class Orchestrator:
    def __init__(self, agents: List[LIAAgent]):
        self.agents = {agent.name: agent for agent in agents}
        self.history = []

    def _get_system_prompt(self) -> str:
        agent_descriptions = "\n\n".join([a.get_capabilities_prompt() for a in self.agents.values()])
        return f"""
You are the LIA Orchestrator. Your job is to take a user request and break it down into a multi-step plan for a swarm of specialized Linux agents.

Available Agents:
{agent_descriptions}

Rules:
1. Analyze the user request.
2. Break it down into sequential tasks.
3. Assign each task to the most appropriate agent.
4. If a task requires information from a previous step, note it as a dependency.
5. Return the plan in JSON format.

Example JSON Output:
{{
  "plan_name": "backup and notify",
  "steps": [
    {{
      "id": 1,
      "agent": "FileAgent",
      "task": "Compress /home/user/Documents to /tmp/backup.tar.gz"
    }},
    {{
      "id": 2,
      "agent": "WebAgent",
      "task": "Email user@example.com that backup is complete"
    }}
  ]
}}
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
                results.append({"step": step['id'], "result": result})
            else:
                logger.warning(f"Agent {agent_name} not found for step {step['id']}")
        
        return results
