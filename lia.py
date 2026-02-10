from core.config import config
from core.llm_bridge import llm_bridge
from core.logger import logger
from core.orchestrator import Orchestrator
from core.workflow_engine import WorkflowEngine
from core.memory_manager import central_memory
from memory.indexer import indexer
from agents.file_agent import FileAgent
from agents.sys_agent import SysAgent
from agents.git_agent import GitAgent
from agents.net_agent import NetAgent
from agents.web_agent import WebAgent
from agents.connection_agent import ConnectionAgent
from agents.docker_agent import DockerAgent
from agents.database_agent import DatabaseAgent
from agents.package_agent import PackageAgent
from ui.gui import start_gui
from ui.tui import start_tui
from core.guardian import guardian
import sys
import json

def main():
    logger.info("Initializing LIA...")
    
    # Start the Guardian background monitor
    guardian.start()
    
    # Initialize all Specialist Agents (Dynamic Swarm — auto-scales)
    agents = [
        FileAgent(),
        SysAgent(),
        GitAgent(),
        NetAgent(),
        WebAgent(),
        ConnectionAgent(),
        DockerAgent(),
        DatabaseAgent(),
        PackageAgent()
    ]
    orchestrator = Orchestrator(agents)
    workflow_engine = WorkflowEngine(orchestrator)
    
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        
        # --- Direct Ask (CLI query without GUI) ---
        if cmd == "ask":
            query = " ".join(sys.argv[2:])
            if not query:
                print("Usage: python lia.py ask <your question>")
                return
            logger.info(f"CLI Query: {query}")
            results = orchestrator.run(query)
            print(f"\n{'═' * 50}")
            print(f"  LIA Response")
            print(f"{'═' * 50}")
            for res in results:
                status = "✅" if "Error" not in str(res.get('result', '')) else "❌"
                print(f"  Step {res['step']}: {status} {res['result']}")
            print(f"{'═' * 50}\n")
            return

        # --- Semantic Index ---
        if cmd == "index":
            logger.info("Starting manual index...")
            count = indexer.index_files(".")
            print(f"✅ Indexed {count} files in the current directory.")
            return

        # --- Semantic Search ---
        if cmd == "search":
            query = " ".join(sys.argv[2:])
            if not query:
                print("Usage: python lia.py search <query>")
                return
            results = indexer.search(query)
            print("\n--- SEMANTIC SEARCH RESULTS ---")
            for res in results:
                print(f"Score: {res['score']:.4f} | Path: {res['metadata']['path']}")
            print("-------------------------------\n")
            return

        # --- Workflow Execution ---
        if cmd == "run":
            workflow_name = sys.argv[2] if len(sys.argv) > 2 else None
            if not workflow_name:
                # List available workflows
                workflows = workflow_engine.list_workflows()
                print("\n--- Available Workflows ---")
                for wf in workflows:
                    print(f"  • {wf}")
                print(f"\nUsage: python lia.py run <workflow_name>")
                print("----------------------------\n")
                return
            logger.info(f"Executing workflow: {workflow_name}")
            results = workflow_engine.execute_workflow(workflow_name)
            print(f"\n{'═' * 50}")
            print(f"  Workflow: {workflow_name}")
            print(f"{'═' * 50}")
            if isinstance(results, str):
                print(f"  {results}")
            else:
                for res in results:
                    if "error" in res:
                        print(f"  Step {res['step']}: ❌ {res['error']}")
                    else:
                        print(f"  Step {res['step']}: ✅ {res['result']}")
            print(f"{'═' * 50}\n")
            return

        # --- GUI ---
        if cmd == "gui":
            logger.info("Launching LIA Control Center (GUI)...")
            start_gui(orchestrator, workflow_engine)
            return

        # --- TUI ---
        if cmd == "tui":
            logger.info("Launching LIA Terminal Interface (TUI)...")
            start_tui(orchestrator, workflow_engine)
            return

        # --- Status ---
        if cmd == "status":
            provider = config.get('llm.provider')
            agent_count = len(orchestrator.agents)
            print(f"\n{'═' * 40}")
            print(f"  LIA STATUS")
            print(f"{'═' * 40}")
            print(f"  Provider:     {provider}")
            print(f"  Model:        {config.get('llm.model')}")
            print(f"  Agents:       {agent_count} specialists")
            print(f"  Memory:       Ready")
            print(f"  Sandbox:      {'ON' if config.get('security.sandbox_enabled') else 'OFF'}")
            print(f"  Dry Run:      {'ON' if config.get('security.dry_run') else 'OFF'}")
            print(f"{'═' * 40}")
            print(f"  Agents: {', '.join(orchestrator.agents.keys())}")
            print(f"{'═' * 40}\n")
            return

        # --- Help ---
        if cmd == "help" or cmd == "--help":
            print_help()
            return

        # --- Unknown command ---
        print(f"Unknown command: '{cmd}'. Run 'python lia.py help' for usage.")
        return

    # Default: Launch GUI
    logger.info("No arguments. Launching GUI...")
    start_gui(orchestrator, workflow_engine)


def print_help():
    print(f"""
{'═' * 50}
  LIA — Local Intelligence Agent
{'═' * 50}

  COMMANDS:
    ask <query>         Run a natural language task via CLI
    gui                 Launch the desktop GUI
    tui                 Launch the terminal UI (SSH-friendly)
    run <workflow>      Execute a YAML workflow
    run                 List available workflows
    index               Index current directory for semantic search
    search <query>      Semantic file search
    status              Show system status and agent list
    help                Show this message

  EXAMPLES:
    python lia.py ask "check my disk space"
    python lia.py ask "find all PDF files in Documents"
    python lia.py run friday_routine
    python lia.py gui
    python lia.py status

{'═' * 50}
""")


if __name__ == "__main__":
    main()
