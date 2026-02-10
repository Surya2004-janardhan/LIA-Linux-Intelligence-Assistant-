import json
import asyncio
from typing import List, Dict, Any
from core.llm_bridge import llm_bridge
from core.logger import logger
from core.audit import audit_manager
from core.context_engine import context_engine
from core.feedback import feedback_manager
from core.safety import safety_guard
from agents.base_agent import LIAAgent

class Orchestrator:
    def __init__(self, agents: List[LIAAgent]):
        self.agents = {agent.name: agent for agent in agents}
        self.history = []

    def _get_system_prompt(self, context: str = "") -> str:
        agent_descriptions = "\n".join([f"- {a.get_capabilities_prompt()}" for a in self.agents.values()])
        
        prompt = f"""You are the LIA Orchestrator. Break user requests into tasks for specialized agents.

Agents:
{agent_descriptions}

Return JSON only:
{{"plan_name": "name", "steps": [{{"id": 1, "agent": "AgentName", "task": "specific task"}}]}}

Rules: Pick the BEST agent per task. Use exact agent names."""
        
        if context:
            prompt += f"\n\nCurrent System Context:\n{context}"
        
        return prompt

    async def plan(self, user_query: str) -> Dict[str, Any]:
        try:
            if not user_query or not user_query.strip():
                return {"error": "Empty query provided", "steps": []}
            
            logger.info(f"Generating plan for: {user_query}")
            
            # 1. Check RAG: Do we have a known-good command for this?
            past_commands = feedback_manager.find_similar(user_query, min_rating=4)
            rag_hint = ""
            if past_commands:
                rag_hint = "\n\nPast successful commands for similar queries:\n"
                for cmd in past_commands[:2]:
                    rag_hint += f"  Query: {cmd['query']} → Agent: {cmd['agent']}, Tool: {cmd['tool']}\n"
            
            # 2. Gather system context (Sync for now, or make context engine async)
            context = context_engine.get_context(user_query)
            
            # 3. Build prompt
            system_prompt = self._get_system_prompt(context)
            if rag_hint:
                system_prompt += rag_hint
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ]
            
            # LLM call (wrapped for async)
            response_text = await asyncio.to_thread(llm_bridge.generate, messages, {"type": "json_object"})
            
            if not response_text:
                return {"error": "LLM returned empty response", "steps": []}
            
            if "Error connecting" in response_text:
                return {"error": response_text, "steps": []}
            
            # Clean response
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip()
            
            plan = json.loads(json_str)
            
            if not isinstance(plan, dict) or "steps" not in plan:
                return {"error": "Invalid plan structure from LLM", "steps": []}
            
            logger.info(f"Plan: {plan.get('plan_name', 'Unnamed')} ({len(plan.get('steps', []))} steps)")
            return plan
            
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON from LLM: {str(e)}", "steps": []}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}", "steps": []}

    async def run(self, user_query: str):
        """Executes the full plan asynchronously."""
        try:
            plan = await self.plan(user_query)
            
            if "error" in plan:
                return [{"step": 0, "result": f"Planning Error: {plan['error']}"}]
            
            results = []
            
            # For simplicity, sequential execution awaiting each step
            # Could upgrade to concurrent execution if steps are independent
            
            for step in plan.get("steps", []):
                agent_name = step.get("agent")
                task = step.get("task")
                
                if not agent_name or not task:
                    results.append({"step": step.get('id', '?'), "result": "Error: Invalid step"})
                    continue
                
                if agent_name in self.agents:
                    try:
                        logger.info(f"Step {step['id']}: [{agent_name}] -> {task}")
                        
                        # Execute Async
                        result = await self.agents[agent_name].execute(task)
                        
                        # Record for RAG
                        success = "Error" not in str(result)
                        feedback_manager.record_command(
                            query=user_query, agent=agent_name,
                            tool="", command=task, result=str(result),
                            success=success
                        )
                        
                        # Audit
                        audit_manager.log_action(agent_name, task, result, 
                            status="success" if success else "error")
                        
                        results.append({"step": step['id'], "result": result})
                        
                    except Exception as e:
                        error_msg = f"Agent {agent_name} crashed: {str(e)}"
                        logger.error(error_msg)
                        audit_manager.log_action(agent_name, task, error_msg, status="error")
                        results.append({"step": step['id'], "result": f"Error: {error_msg}"})
                else:
                    available = ', '.join(self.agents.keys())
                    results.append({"step": step['id'], 
                        "result": f"Error: Agent '{agent_name}' not found. Available: {available}"})
            
            # Store in history
            self.history.append({"query": user_query, "results": results})
            
            return results
            
        except Exception as e:
            logger.error(f"Orchestrator run failed: {e}")
            return [{"step": 0, "result": f"Fatal Error: {str(e)}"}]
