import yaml
import os
from typing import List, Dict, Any
from core.logger import logger

class WorkflowEngine:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.workflows_dir = "workflows"
        if not os.path.exists(self.workflows_dir):
            os.makedirs(self.workflows_dir)

    def load_workflow(self, workflow_name: str) -> Dict[str, Any]:
        """Reads a YAML workflow file from the workflows directory."""
        path = os.path.join(self.workflows_dir, f"{workflow_name}.yaml")
        if not os.path.exists(path):
            logger.error(f"Workflow file not found: {path}")
            return None
        
        with open(path, 'r') as f:
            try:
                return yaml.safe_load(f)
            except Exception as e:
                logger.error(f"Failed to parse YAML workflow: {e}")
                return None

    def execute_workflow(self, workflow_name: str, variables: Dict[str, str] = None):
        """Executes a predefined multi-step YAML workflow."""
        workflow = self.load_workflow(workflow_name)
        if not workflow:
            return f"Error: Workflow {workflow_name} not found or invalid."

        logger.info(f"Starting workflow execution: {workflow.get('name', workflow_name)}")
        steps = workflow.get('steps', [])
        results = []

        for step in steps:
            agent_name = step.get('agent')
            task = step.get('task')
            
            # Replace variables if provided (e.g., {{filename}})
            if variables:
                for var, val in variables.items():
                    task = task.replace(f"{{{{{var}}}}}", val)

            logger.info(f"Workflow Step: [{agent_name}] -> {task}")
            
            # Use orchestrator to route to the correct agent
            if agent_name in self.orchestrator.agents:
                agent = self.orchestrator.agents[agent_name]
                result = agent.execute(task)
                results.append({"step": step.get('id', 'unknown'), "task": task, "result": result})
            else:
                error = f"Agent {agent_name} not found."
                logger.error(error)
                results.append({"step": step.get('id', 'unknown'), "error": error})
        
        return results

    def list_workflows(self):
        """Returns a list of available workflow names."""
        if not os.path.exists(self.workflows_dir):
            return []
        return [f.replace('.yaml', '') for f in os.listdir(self.workflows_dir) if f.endswith('.yaml')]
