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
import asyncio

def _rich_print(text: str):
    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        console.print(Panel(text, border_style="cyan", padding=(0, 1)))
    except ImportError:
        print(text)

def _print_results(results, title="LIA Response"):
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        
        console = Console()
        table = Table(show_header=True, header_style="bold cyan", 
                      border_style="dim", pad_edge=False)
        table.add_column("Step", style="dim", width=6)
        table.add_column("Status", width=4)
        table.add_column("Result", style="white")
        
        for res in results:
            result_str = str(res.get('result', ''))
            is_error = "Error" in result_str
            status = "❌" if is_error else "✅"
            style = "red" if is_error else "green"
            table.add_row(str(res['step']), status, result_str[:200])
        
        console.print(Panel(table, title=f"[bold]{title}[/bold]", border_style="cyan"))
    except ImportError:
        print(f"\n{'═' * 50}")
        print(f"  {title}")
        print(f"{'═' * 50}")
        for res in results:
            status = "✅" if "Error" not in str(res.get('result', '')) else "❌"
            print(f"  Step {res['step']}: {status} {res['result']}")
        print(f"{'═' * 50}\n")

async def async_main():
    logger.info("Initializing LIA (Async)...")
    
    # Check setup (interactive prompt if needed)
    central_memory._ensure_setup()
    
    # Register cleanup hooks
    os_layer.register_shutdown_hook(central_memory.close)
    os_layer.register_shutdown_hook(audit_manager.close)
    os_layer.register_shutdown_hook(feedback_manager.close)
    
    # Start background monitor
    guardian.start()
    
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
        
        if cmd == "ask":
            query = " ".join(sys.argv[2:])
            if not query:
                print("Usage: python lia.py ask <your question>")
                return
            logger.info(f"CLI Query: {query}")
            results = await orchestrator.run(query)
            _print_results(results)
            
            # Feedback
            try:
                # Use standard input for synchronous prompt (avoid blocking loop for long if possible)
                # But input() blocks. In a real async CLI, we'd use aioconsole.
                # Since this is a one-shot command, blocking input() at the END is acceptable.
                rating = input("  Rate this response (1-5, or Enter to skip): ").strip()
                if rating and rating.isdigit():
                    feedback_manager.rate_last_command(int(rating))
                    print(f"  {'⭐' * int(rating)} Feedback recorded.")
            except (EOFError, KeyboardInterrupt):
                pass
            return

        if cmd == "explain":
            command = " ".join(sys.argv[2:])
            if not command:
                print("Usage: python lia.py explain <command>")
                return
            result = explain_command(command)
            _rich_print(result)
            return

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

        if cmd == "status":
            info = os_layer.get_system_summary()
            agent_count = len(orchestrator.agents)
            fb_stats = feedback_manager.get_feedback_stats()
            _rich_print(
                f"LIA STATUS — {info['hostname']} (Linux Intelligence Agent)\n"
                f"{'─' * 35}\n"
                f"Distro:    {info.get('distro', 'Unknown')}\n"
                f"Kernel:    {info.get('kernel', 'Unknown')}\n"
                f"Arch:      {info['arch']}\n"
                f"Agents:    {agent_count} specialists\n"
                f"Sandbox:   {'ON' if config.get('security.sandbox_enabled') else 'OFF'}\n"
                f"Feedback:  {fb_stats['total_feedback']} ratings\n"
            )
            return

        if cmd in ("help", "--help", "-h"):
            print_help()
            return

        print(f"Unknown command: '{cmd}'. Run 'lia help' for usage.")
        return

    # Default to GUI (not async-compatible yet without major refactor, fallback to help)
    print_help()

def print_help():
    help_text = """
LIA — Linux Intelligence Agent (Async Core)

COMMANDS:
  ask <query>         Execute tasks using natural language
  explain <cmd>       Explain shell one-liners
  history             Show command history
  status              Show system status
  help                Show this message
  
SETUP:
  On first run, LIA will ask for permission to access specific directories.
  This 'Root Context' is customizable and prevents unauthorized access.
"""
    try:
        from rich.console import Console
        from rich.panel import Panel
        Console().print(Panel(help_text, title="LIA CLI", border_style="cyan"))
    except ImportError:
        print(help_text)

def main():
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")

if __name__ == "__main__":
    main()
