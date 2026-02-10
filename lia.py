from core.config import config
from core.llm_bridge import llm_bridge
from core.logger import logger
from core.orchestrator import Orchestrator
from core.workflow_engine import WorkflowEngine
from core.memory_manager import central_memory
from core.os_layer import os_layer
from core.audit import audit_manager
from core.feedback import feedback_manager
from core.explain import explain_command
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

def main():
    logger.info("Initializing LIA (Linux Intelligence Agent)...")
    
    # Register cleanup hooks for graceful shutdown
    os_layer.register_shutdown_hook(central_memory.close)
    os_layer.register_shutdown_hook(audit_manager.close)
    os_layer.register_shutdown_hook(feedback_manager.close)
    
    # Start background monitor
    guardian.start()
    
    # Initialize agents (Dynamic Swarm)
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
        
        # ─── ASK ──────────────────────────────────────────────────
        if cmd == "ask":
            query = " ".join(sys.argv[2:])
            if not query:
                print("Usage: python lia.py ask <your question>")
                return
            logger.info(f"CLI Query: {query}")
            results = orchestrator.run(query)
            # Use rich output if available
            try:
                from rich.console import Console
                from rich.panel import Panel
                from rich.table import Table
                
                console = Console()
                table = Table(show_header=True, header_style="bold cyan", border_style="dim")
                table.add_column("Step", width=6)
                table.add_column("Status", width=4)
                table.add_column("Result", style="white")
                
                for res in results:
                    status = "❌" if "Error" in str(res.get('result', '')) else "✅"
                    table.add_row(str(res['step']), status, str(res['result'])[:200])
                
                console.print(Panel(table, title="LIA Response", border_style="cyan"))
            except ImportError:
                # Fallback
                print(f"\n{'═' * 50}")
                print(f"  LIA Response")
                print(f"{'═' * 50}")
                for res in results:
                    status = "✅" if "Error" not in str(res.get('result', '')) else "❌"
                    print(f"  Step {res['step']}: {status} {res['result']}")
                print(f"{'═' * 50}\n")
            
            # Prompt for feedback
            try:
                rating = input("  Rate this response (1-5, or Enter to skip): ").strip()
                if rating and rating.isdigit():
                    feedback_manager.rate_last_command(int(rating))
                    print(f"  {'⭐' * int(rating)} Feedback recorded.")
            except (EOFError, KeyboardInterrupt):
                pass
            return

        # ─── EXPLAIN ──────────────────────────────────────────────
        if cmd == "explain":
            command = " ".join(sys.argv[2:])
            if not command:
                print("Usage: python lia.py explain <command>")
                print('Example: python lia.py explain "grep -r foo . | awk \'{print $1}\'"')
                return
            result = explain_command(command)
            try: 
                from rich.console import Console 
                from rich.panel import Panel
                Console().print(Panel(result, border_style="cyan", padding=(0, 1)))
            except ImportError:
                print(result)
            return

        # ─── HISTORY ──────────────────────────────────────────────
        if cmd == "history":
            history = feedback_manager.get_history(limit=20)
            if not history:
                print("No command history yet.")
                return
            try:
                from rich.console import Console
                from rich.table import Table
                console = Console()
                table = Table(title="Command History", border_style="dim")
                table.add_column("Time", style="dim", width=19)
                table.add_column("Query", width=30)
                table.add_column("Agent", style="cyan", width=15)
                table.add_column("Rating", width=8)
                for h in history:
                    rating_str = "⭐" * h['rating'] if h['rating'] else "—"
                    table.add_row(h['timestamp'][:19], h['query'][:30], h['agent'], rating_str)
                console.print(table)
            except ImportError:
                for h in history:
                    print(f"  {h['timestamp'][:19]} | {h['query'][:30]} | {h['agent']}")
            return

        # ─── FEEDBACK STATS ───────────────────────────────────────
        if cmd == "feedback":
            stats = feedback_manager.get_feedback_stats()
            print(f"Total Feedback: {stats['total_feedback']}")
            print(f"Avg Rating:     {stats['avg_rating']} / 5")
            print(f"Positive (4-5): {stats['positive']}")
            print(f"Negative (1-2): {stats['negative']}")
            return

        # ─── INDEX ────────────────────────────────────────────────
        if cmd == "index":
            count = indexer.index_files(".")
            print(f"✅ Indexed {count} files in the current directory.")
            return

        # ─── SEARCH ───────────────────────────────────────────────
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

        # ─── STATUS ───────────────────────────────────────────────
        if cmd == "status":
            info = os_layer.get_system_summary()
            agent_count = len(orchestrator.agents)
            fb_stats = feedback_manager.get_feedback_stats()
            try:
                from rich.console import Console
                from rich.panel import Panel
                Console().print(Panel(
                    f"LIA STATUS — {info['hostname']} (Linux Intelligence Agent)\n"
                    f"{'─' * 35}\n"
                    f"Distro:    {info.get('distro', 'Unknown')}\n"
                    f"Kernel:    {info.get('kernel', 'Unknown')}\n"
                    f"Arch:      {info['arch']}\n"
                    f"Python:    {info['python']}\n"
                    f"Agents:    {agent_count} specialists\n"
                    f"Sandbox:   {'ON' if config.get('security.sandbox_enabled') else 'OFF'}\n"
                    f"Feedback:  {fb_stats['total_feedback']} ratings (avg: {fb_stats['avg_rating']})\n"
                    f"{'─' * 35}\n"
                    f"Agents: {', '.join(orchestrator.agents.keys())}",
                    title="System Status", border_style="green"
                ))
            except ImportError:
                print(f"LIA STATUS — {info['hostname']} (Linux Intelligence Agent)")
                print(f"Distro:    {info.get('distro', 'Unknown')}")
                print(f"Kernel:    {info.get('kernel', 'Unknown')}")
                print(f"Arch:      {info['arch']}")
                print(f"Agents:    {agent_count}")
            return

        # ─── HELP ─────────────────────────────────────────────────
        if cmd in ("help", "--help", "-h"):
            print_help()
            return
            
        print(f"Unknown command: '{cmd}'. Run 'lia help' for usage.")
        return

    # Default logic (TUI/GUI if desired, or help)
    print_help()


def print_help():
    help_text = """
LIA — Linux Intelligence Agent

COMMANDS:
  ask <query>         Execute tasks using natural language
  explain <cmd>       Explain shell one-liners using LLM
  history             Show past successful commands (RAG)
  feedback            Show feedback statistics
  status              Show distro, kernel, and agent status
  search <query>      Semantic file search
  index               Index current directory
  
EXAMPLES:
  lia ask "why is my server laggy?"
  lia ask "restart nginx and show logs"
  lia explain "chmod 755 /var/www/html"
"""
    try:
        from rich.console import Console
        from rich.panel import Panel
        Console().print(Panel(help_text, title="LIA CLI", border_style="cyan"))
    except ImportError:
        print(help_text)


if __name__ == "__main__":
    main()
