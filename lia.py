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


def _rich_print(text: str):
    """Print with syntax highlighting if rich is available, plain otherwise."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        console = Console()
        console.print(Panel(text, border_style="cyan", padding=(0, 1)))
    except ImportError:
        print(text)


def _print_results(results, title="LIA Response"):
    """Formats results with color/highlighting."""
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


def main():
    logger.info("Initializing LIA...")
    
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
            _print_results(results)
            
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
                print('Example: python lia.py explain "find . -name *.py | xargs grep import"')
                return
            result = explain_command(command)
            _rich_print(result)
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
            _rich_print(
                f"Total Feedback: {stats['total_feedback']}\n"
                f"Avg Rating:     {stats['avg_rating']} / 5\n"
                f"Positive (4-5): {stats['positive']}\n"
                f"Negative (1-2): {stats['negative']}"
            )
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

        # ─── RUN WORKFLOW ─────────────────────────────────────────
        if cmd == "run":
            workflow_name = sys.argv[2] if len(sys.argv) > 2 else None
            if not workflow_name:
                workflows = workflow_engine.list_workflows()
                print("\n--- Available Workflows ---")
                for wf in workflows:
                    print(f"  • {wf}")
                print(f"\nUsage: python lia.py run <workflow_name>")
                print("----------------------------\n")
                return
            results = workflow_engine.execute_workflow(workflow_name)
            _print_results(results if isinstance(results, list) else [{"step": 1, "result": results}],
                          title=f"Workflow: {workflow_name}")
            return

        # ─── GUI ──────────────────────────────────────────────────
        if cmd == "gui":
            start_gui(orchestrator, workflow_engine)
            return

        # ─── TUI ──────────────────────────────────────────────────
        if cmd == "tui":
            start_tui(orchestrator, workflow_engine)
            return

        # ─── STATUS ───────────────────────────────────────────────
        if cmd == "status":
            info = os_layer.get_system_summary()
            agent_count = len(orchestrator.agents)
            fb_stats = feedback_manager.get_feedback_stats()
            _rich_print(
                f"LIA STATUS — {info['hostname']}\n"
                f"{'─' * 35}\n"
                f"Platform:  {info['platform']}/{info['arch']}\n"
                f"Python:    {info['python']}\n"
                f"Provider:  {config.get('llm.provider')}\n"
                f"Model:     {config.get('llm.model')}\n"
                f"Agents:    {agent_count} specialists\n"
                f"Memory:    SQLite + FAISS\n"
                f"Sandbox:   {'ON' if config.get('security.sandbox_enabled') else 'OFF'}\n"
                f"Feedback:  {fb_stats['total_feedback']} ratings (avg: {fb_stats['avg_rating']})\n"
                f"{'─' * 35}\n"
                f"Agents: {', '.join(orchestrator.agents.keys())}"
            )
            return

        # ─── HELP ─────────────────────────────────────────────────
        if cmd in ("help", "--help", "-h"):
            print_help()
            return

        # Unknown
        print(f"Unknown command: '{cmd}'. Run 'python lia.py help' for usage.")
        return

    # Default: Launch GUI
    start_gui(orchestrator, workflow_engine)


def print_help():
    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        help_text = """[bold cyan]COMMANDS:[/bold cyan]
  [green]ask[/green] <query>         Run a natural language task
  [green]explain[/green] <command>   Break down a complex command
  [green]gui[/green]                 Launch desktop GUI
  [green]tui[/green]                 Launch terminal UI (SSH-friendly)
  [green]run[/green] <workflow>      Execute a YAML workflow
  [green]run[/green]                 List available workflows
  [green]index[/green]               Index directory for semantic search
  [green]search[/green] <query>      Semantic file search
  [green]history[/green]             Show command history with ratings
  [green]feedback[/green]            Show feedback statistics
  [green]status[/green]              Show system status
  [green]help[/green]                Show this message

[bold cyan]EXAMPLES:[/bold cyan]
  [dim]# Simple tasks[/dim]
  python lia.py ask "check my disk space"
  python lia.py ask "what's using all my RAM?"
  
  [dim]# Multi-step tasks[/dim]
  python lia.py ask "find all .log files bigger than 100MB and list them"
  python lia.py ask "check git status, commit everything, then show the log"
  python lia.py ask "ping google.com and scan ports on localhost"
  
  [dim]# Command explanation[/dim]
  python lia.py explain "find . -name '*.py' | xargs grep -l 'import os'"
  python lia.py explain "tar -czf backup.tar.gz --exclude=node_modules ."
  
  [dim]# Workflows[/dim]
  python lia.py run friday_routine"""
        console.print(Panel(help_text, title="[bold]LIA — Local Intelligence Agent[/bold]", 
                           border_style="cyan"))
    except ImportError:
        print(f"""
{'═' * 50}
  LIA — Local Intelligence Agent
{'═' * 50}

  COMMANDS:
    ask <query>         Run a natural language task
    explain <command>   Break down a complex command
    gui                 Launch desktop GUI
    tui                 Launch terminal UI
    run <workflow>      Execute a YAML workflow
    history             Show command history
    feedback            Show feedback statistics
    status              Show system status
    help                Show this message

  EXAMPLES:
    python lia.py ask "check my disk space"
    python lia.py ask "what's using all my RAM?"
    python lia.py ask "check git status, commit everything, then show the log"
    python lia.py explain "find . -name '*.py' | xargs grep import"
    python lia.py run friday_routine

{'═' * 50}
""")


if __name__ == "__main__":
    main()
