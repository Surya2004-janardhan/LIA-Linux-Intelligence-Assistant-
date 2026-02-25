from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Log, Static, Label
from textual.containers import Container, Horizontal, Vertical
from core.logger import logger
import json

class WIATUI(App):
    """A Textual TUI for WIA."""

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
        
        # Clear input early to improve responsiveness
        event.input.value = ""
        log.write_line(f"User > {query}")

        try:
            async for update in self.orchestrator.run_stream(query):
                state = update.get("status")
                
                if state == "planning":
                    status.update("Orchestrating...")
                
                elif state == "planned":
                    log.write_line("PLAN GENERATED:")
                    for step in update["plan"].get("steps", []):
                        log.write_line(f" - [{step['agent']}] {step['task']}")
                    log.write_line("Executing Swarm...")
                
                elif state == "executing":
                    status.update(f"Executing: {update['agent']}")
                    log.write_line(f" > [{update['agent']}] working on: {update['task']}...")
                
                elif state == "completed":
                    log.write_line(f" ✅ Step {update['step']} finished.")
                
                elif state == "error":
                    log.write_line(f" ❌ Error: {update.get('message', 'Unknown error')}")
                    if "step" not in update: # Fatal planning error
                        status.update("Error")
                
                elif state == "finished":
                    log.write_line("--- EXECUTION FINISHED ---")
                    status.update("Idle")
                    for res in update["results"]:
                         # Check if result is already long, truncate if needed for TUI
                         res_str = str(res['result'])
                         if len(res_str) > 500:
                             res_str = res_str[:500] + "..."
                         log.write_line(f"Step {res['step']} Result: {res_str}")

        except Exception as e:
            logger.error(f"TUI Error: {e}")
            log.write_line(f"Fatal UI Error: {str(e)}")
            status.update("Error")

    def action_clear(self) -> None:
        self.query_one("#results_log", Log).clear()

def start_tui(orchestrator, workflow_engine):
    app = WIATUI(orchestrator, workflow_engine)
    app.run()
