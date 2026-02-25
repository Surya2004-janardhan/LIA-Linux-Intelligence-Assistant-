import json
import asyncio
from typing import List, Dict, Any
from core.llm_bridge import llm_bridge
from core.logger import logger
from core.audit import audit_manager
from core.context_engine import context_engine
from core.feedback import feedback_manager
from core.safety import safety_guard
from core.telemetry import telemetry
import time
from agents.base_agent import WIAAgent

class Orchestrator:
    def __init__(self, agents: List[WIAAgent]):
        self.agents = {agent.name: agent for agent in agents}
        self.history = []

    def _get_system_prompt(self, context: str = "") -> str:
        agent_descriptions = "\n".join([f"- {a.get_capabilities_prompt()}" for a in self.agents.values()])
        
        prompt = f"""You are the WIA Orchestrator. Break user requests into tasks for specialized agents.

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

    async def run_stream(self, user_query: str):
        """Yields streaming status updates during execution."""
        try:
            yield {"status": "planning", "message": "Analyzing query..."}
            plan = await self.plan(user_query)
            
            if "error" in plan:
                yield {"status": "error", "message": f"Planning Error: {plan['error']}"}
                return

            yield {"status": "planned", "plan": plan}
            
            results = []
            for step in plan.get("steps", []):
                agent_name = step.get("agent")
                task = step.get("task")
                
                if not agent_name or not task:
                    yield {"status": "error", "message": f"Invalid step {step.get('id', '?')}"}
                    continue
                
                if agent_name in self.agents:
                    yield {"status": "executing", "step": step['id'], "agent": agent_name, "task": task}
                    start_time = time.time()
                    try:
                        logger.info(f"Step {step['id']}: [{agent_name}] -> {task}")
                        
                        # Execute Async
                        result = await self.agents[agent_name].execute(task)
                        duration = time.time() - start_time
                        
                        # Record for RAG
                        success = "Error" not in str(result)
                        feedback_manager.record_command(
                            query=user_query, agent=agent_name,
                            tool="", command=task, result=str(result),
                            success=success
                        )
                        
                        # Telemetry
                        telemetry.log_command(agent_name, success, duration)
                        
                        # Audit
                        audit_manager.log_action(agent_name, task, result, 
                            status="success" if success else "error")
                        
                        step_res = {"step": step['id'], "result": result}
                        results.append(step_res)
                        yield {"status": "completed", "step": step['id'], "result": result}
                        
                    except Exception as e:
                        error_msg = f"Agent {agent_name} crashed: {str(e)}"
                        logger.error(error_msg)
                        audit_manager.log_action(agent_name, task, error_msg, status="error")
                        yield {"status": "error", "step": step['id'], "message": error_msg}
                        results.append({"step": step['id'], "result": f"Error: {error_msg}"})
                else:
                    available = ', '.join(self.agents.keys())
                    msg = f"Agent '{agent_name}' not found. Available: {available}"
                    yield {"status": "error", "step": step['id'], "message": msg}
                    results.append({"step": step['id'], "result": f"Error: {msg}"})
            
            # Store in history
            self.history.append({"query": user_query, "results": results})
            yield {"status": "finished", "results": results}
            
        except Exception as e:
            logger.error(f"Orchestrator stream failed: {e}")
            yield {"status": "error", "message": f"Fatal Error: {str(e)}"}

    async def run(self, user_query: str):
        """Executes the full plan asynchronously (wrapper for run_stream)."""
        results = []
        async for update in self.run_stream(user_query):
            if update["status"] == "finished":
                results = update["results"]
            elif update["status"] == "error" and "step" not in update:
                return [{"step": 0, "result": f"Error: {update['message']}"}]
        return results
