from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Log, Static, Label
from textual.containers import Container, Horizontal, Vertical
from core.logger import logger
import json

class LIATUI(App):
    """A Textual TUI for LIA."""

    CSS = """
    Screen {
        background: #0F1117;
    }

    #input_container {
        dock: top;
        height: 5;
        padding: 1;
        background: #1A1D26;
    }

    #main_container {
        layout: horizontal;
    }

    #results_log {
        width: 70%;
        background: #1A1D26;
        border: solid #2A2E3D;
        color: #FFFFFF;
    }

    #status_sidebar {
        width: 30%;
        background: #0F1117;
        border-left: solid #2A2E3D;
        padding: 1;
    }

    .status_label {
        color: #00D2FF;
        margin-bottom: 1;
    }

    Input {
        border: solid #2A2E3D;
        background: #0F1117;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("c", "clear", "Clear Results"),
    ]

    def __init__(self, orchestrator, workflow_engine):
        super().__init__()
        self.orchestrator = orchestrator
        self.workflow_engine = workflow_engine

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Input(placeholder="English -> Linux -> Agents -> Done (100% Local)", id="user_input"),
            id="input_container"
        )
        yield Container(
            Log(id="results_log"),
            Vertical(
                Label("AGENT FEED", classes="status_label"),
                Static("Idle", id="agent_status"),
                id="status_sidebar"
            ),
            id="main_container"
        )
        yield Footer()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value
        if not query:
            return

        log = self.query_one("#results_log", Log)
        status = self.query_one("#agent_status", Static)
        status.update("Orchestrating...")
        log.write_line(f"User > {query}")

        # Clear input
        event.input.value = ""

        # Run Planning (Off-thread suggested for real TUI, but keeping it simple for MVP)
        plan = self.orchestrator.plan(query)
        
        if "error" in plan:
            log.write_line(f"Error: {plan['error']}")
            status.update("Error")
            return

        log.write_line("PLAN GENERATED:")
        for step in plan.get("steps", []):
            log.write_line(f" - [{step['agent']}] {step['task']}")
        
        # In TUI we auto-confirm for now or could add a toggle
        log.write_line("Executing...")
        status.update("Executing Agents...")
        
        results = self.orchestrator.run(query)
        
        log.write_line("RESULTS:")
        for res in results:
            log.write_line(f"Step {res['step']}: {res['result']}")
        
        status.update("Completed")

    def action_clear(self) -> None:
        self.query_one("#results_log", Log).clear()

def start_tui(orchestrator, workflow_engine):
    app = LIATUI(orchestrator, workflow_engine)
    app.run()
