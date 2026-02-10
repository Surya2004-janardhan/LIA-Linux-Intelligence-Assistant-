from core.config import config
from core.llm_bridge import llm_bridge
from core.logger import logger
from core.orchestrator import Orchestrator
from core.workflow_engine import WorkflowEngine
from memory.indexer import indexer
from agents.file_agent import FileAgent
from agents.sys_agent import SysAgent
from agents.git_agent import GitAgent
from agents.net_agent import NetAgent
from agents.web_agent import WebAgent
import sys
import json

def main():
    logger.info("Initializing LIA...")
    
    # Initialize all Specialist Agents
    agents = [
        FileAgent(),
        SysAgent(),
        GitAgent(),
        NetAgent(),
        WebAgent()
    ]
    orchestrator = Orchestrator(agents)
    workflow_engine = WorkflowEngine(orchestrator)
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        if cmd == "index":
            logger.info("Phase 2: Starting manual index...")
            count = indexer.index_files(".")
            print(f"✅ Indexed {count} files in the current directory.")
            return

        if cmd == "search":
            query = " ".join(sys.argv[2:])
            logger.info(f"Phase 2: Searching for '{query}'...")
            results = indexer.search(query)
            print("\n--- SEMANTIC SEARCH RESULTS ---")
            for res in results:
                print(f"Score: {res['score']:.4f} | Path: {res['metadata']['path']}")
            print("-------------------------------\n")
            return

        if cmd == "run":
            workflow_name = sys.argv[2] if len(sys.argv) > 2 else "friday_routine"
            logger.info(f"Phase 6: Executing workflow '{workflow_name}'...")
            results = workflow_engine.execute_workflow(workflow_name)
            print(f"\n--- WORKFLOW RESULTS: {workflow_name} ---")
            for res in results:
                if "error" in res:
                    print(f"Step {res['step']}: ❌ {res['error']}")
                else:
                    print(f"Step {res['step']}: ✅ {res['result']}")
            print("-------------------------------\n")
            return

        if cmd == "ask":
            query = " ".join(sys.argv[2:])
            logger.info(f"Phase 3: Orchestrating for '{query}'...")
            plan = orchestrator.plan(query)
            print("\n--- LIA PLAN ---")
            print(json.dumps(plan, indent=2))
            
            confirm = input("\nExecute this plan? (y/n): ")
            if confirm.lower() == 'y':
                results = orchestrator.run(query)
                print("\n--- EXECUTION RESULTS ---")
                for res in results:
                    print(f"Step {res['step']}: {res['result']}")
            return

    # Default logic (Phase 1)
    provider = config.get('llm.provider')
    logger.info(f"LLM Provider: {provider}")
    logger.info("LIA Ready. Use 'ask <query>' to test Phase 3.")
    
    print("\n--- LIA STATUS ---")
    print(f"Provider: {provider}")
    print(f"Model: {config.get('llm.model')}")
    print("Memory: Ready")
    print("Orchestrator: Ready (6 Core Agents System)")
    print("------------------\n")

if __name__ == "__main__":
    main()
