import flet as ft
from core.logger import logger
from core.config import config
import traceback

class LIAApp:
    def __init__(self, orchestrator, workflow_engine):
        self.orchestrator = orchestrator
        self.workflow_engine = workflow_engine
        self.theme_color = "#00D2FF"

    def main(self, page: ft.Page):
        self.page = page
        page.title = "LIA Control Center"
        page.theme_mode = ft.ThemeMode.DARK
        page.window_width = 1000
        page.window_height = 800
        page.bgcolor = "#0F1117"
        page.fonts = {
            "Outfit": "https://github.com/google/fonts/raw/main/ofl/outfit/Outfit%5Bwght%5D.ttf"
        }
        page.theme = ft.Theme(font_family="Outfit")
        
        # --- ERROR SNACKBAR ---
        self.error_snackbar = ft.SnackBar(
            content=ft.Text(""),
            bgcolor="#D32F2F",
            action="Dismiss"
        )
        page.overlay.append(self.error_snackbar)
        
        # --- UI TABS ---
        self.tabs = ft.Tabs(
            selected_index=0,
            animation_duration=300,
            tabs=[
                ft.Tab(text="Dashboard", icon=ft.icons.DASHBOARD_ROUNDED),
                ft.Tab(text="Settings", icon=ft.icons.SETTINGS_ROUNDED),
                ft.Tab(text="Workflows", icon=ft.icons.AUTO_FIX_HIGH_ROUNDED),
            ],
            expand=False,
        )

        # --- DASHBOARD TAB ---
        self.status_feed = ft.Column(expand=True, scroll=ft.ScrollMode.ALWAYS, spacing=10)
        self.result_display = ft.Container(
            content=ft.Text("Ready for instructions...", color="#666666"),
            bgcolor="#1A1D26",
            padding=20,
            border_radius=15,
            expand=True,
        )

        search_field = ft.TextField(
            hint_text="Ask LIA something...",
            expand=True,
            border_radius=15,
            bgcolor="#1A1D26",
            border_color="#2A2E3D",
            on_submit=lambda e: self.process_query(e.control.value),
        )

        dashboard_content = ft.Column([
            ft.Row([
                ft.Icon(ft.icons.PSYCHOLOGY, color=self.theme_color, size=40),
                ft.Text("LIA Swarm", size=28, weight="bold"),
            ]),
            ft.Row([search_field, ft.IconButton(ft.icons.SEND_ROUNDED, icon_color=self.theme_color, on_click=lambda _: self.process_query(search_field.value))]),
            ft.Row([
                self.result_display,
                ft.Container(
                    content=ft.Column([
                        ft.Text("Agent Feed", weight="bold", color="#AAAAAA"),
                        self.status_feed
                    ]),
                    width=250,
                    bgcolor="#14171F",
                    padding=15,
                    border_radius=15
                )
            ], expand=True)
        ], expand=True)

        # --- SETTINGS TAB ---
        settings_content = ft.Column([
            ft.Text("System Customization", size=24, weight="bold"),
            ft.Text("Manage your local-first intelligence environment.", color="#AAAAAA"),
            ft.Divider(color="#2A2E3D"),
            ft.Switch(label="Enable Firejail Sandbox (Linux Only)", value=config.get('security.sandbox_enabled')),
            ft.Switch(label="Strict Confirmation Mode", value=True),
            ft.Dropdown(
                label="Primary Model (Ollama)",
                value=config.get('llm.model'),
                options=[
                    ft.dropdown.Option("llama3"),
                    ft.dropdown.Option("mistral"),
                    ft.dropdown.Option("codellama"),
                ],
                width=300
            ),
            ft.ElevatedButton("Save Configuration", icon=ft.icons.SAVE, bgcolor=self.theme_color, color="white"),
            ft.Divider(color="#2A2E3D"),
            ft.Text("Audit Log Path: memory/audit_log.db", size=12, color="#666666"),
        ], scroll=ft.ScrollMode.ALWAYS, padding=20, visible=False)

        # --- WORKFLOWS TAB ---
        workflow_list = ft.ListView(expand=True, spacing=10, padding=20, visible=False)
        try:
            for wf in self.workflow_engine.list_workflows():
                workflow_list.controls.append(
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.LAYERS_ROUNDED, color=self.theme_color),
                        title=ft.Text(wf.replace('_', ' ').title()),
                        subtitle=ft.Text("Automation Routine"),
                        trailing=ft.FilledButton("Run", on_click=lambda _, n=wf: self.run_workflow_ui(n)),
                        bgcolor="#1A1D26",
                        shape=ft.RoundedRectangleBorder(radius=10),
                    )
                )
        except Exception as e:
            logger.error(f"Failed to load workflows: {e}")
            workflow_list.controls.append(ft.Text(f"Error loading workflows: {str(e)}", color="red"))

        # Navigation Handling
        def update_view(e):
            dashboard_content.visible = (self.tabs.selected_index == 0)
            settings_content.visible = (self.tabs.selected_index == 1)
            workflow_list.visible = (self.tabs.selected_index == 2)
            page.update()
        
        self.tabs.on_change = update_view

        page.add(
            self.tabs,
            ft.Divider(height=1, color="#2A2E3D"),
            ft.Stack([
                dashboard_content,
                settings_content,
                workflow_list
            ], expand=True)
        )

    def show_error(self, message: str, details: str = None):
        """Displays error in both snackbar and result area."""
        # Snackbar for quick notification
        self.error_snackbar.content.value = message
        self.error_snackbar.open = True
        
        # Detailed error in result area
        error_view = ft.Column([
            ft.Row([
                ft.Icon(ft.icons.ERROR_OUTLINE, color="#D32F2F", size=40),
                ft.Text("Error", size=24, weight="bold", color="#D32F2F")
            ]),
            ft.Divider(color="#D32F2F"),
            ft.Text(message, size=16, color="#FFFFFF"),
        ])
        
        if details:
            error_view.controls.append(ft.Container(
                content=ft.Column([
                    ft.Text("Technical Details:", size=12, weight="bold", color="#AAAAAA"),
                    ft.Text(details, size=11, color="#666666", selectable=True)
                ]),
                bgcolor="#1A1D26",
                padding=10,
                border_radius=8,
                margin=ft.margin.only(top=10)
            ))
        
        self.result_display.content = error_view
        self.page.update()

    def add_status_bubble(self, agent_name, status, color="#00D2FF"):
        bubble = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.CIRCLE, size=8, color=color),
                ft.Text(f"{agent_name}: {status}", size=11, color="#CCCCCC"),
            ]),
            padding=2,
        )
        self.status_feed.controls.insert(0, bubble)
        if len(self.status_feed.controls) > 50:  # Limit feed size
            self.status_feed.controls.pop()
        self.page.update()

    def process_query(self, query):
        if not query:
            self.show_error("Empty Query", "Please enter a task or question for LIA.")
            return
        
        try:
            self.result_display.content = ft.Column([
                ft.ProgressBar(color=self.theme_color),
                ft.Text("Consulting Swarm...")
            ])
            self.page.update()
            
            self.add_status_bubble("Orchestrator", "Analyzing query...")
            
            # Validate Orchestrator
            if not self.orchestrator or not self.orchestrator.agents:
                raise Exception("Orchestrator not initialized or no agents available")
            
            plan = self.orchestrator.plan(query)
            
            # Check for planning errors
            if "error" in plan:
                error_msg = plan.get("error", "Unknown planning error")
                self.show_error("Planning Failed", f"The orchestrator couldn't create a plan: {error_msg}")
                self.add_status_bubble("Orchestrator", "Planning failed", color="red")
                return

            # Check for empty plan
            if not plan.get("steps"):
                self.show_error("No Actions Planned", "The orchestrator couldn't determine how to handle this request. Try rephrasing or being more specific.")
                return

            # Display plan
            steps = [ft.Text("Execution Plan Generated", weight="bold", size=16), ft.Divider()]
            for step in plan.get('steps', []):
                steps.append(ft.Row([
                    ft.Icon(ft.icons.CHECK_CIRCLE_OUTLINE, size=16, color=self.theme_color),
                    ft.Text(f"[{step['agent']}] {step['task']}", size=14)
                ]))
            
            confirm_btn = ft.ElevatedButton(
                "Start Swarm Execution",
                icon=ft.icons.PLAY_ARROW,
                on_click=lambda _: self.execute_plan(query),
                bgcolor=self.theme_color,
                color="white"
            )
            steps.append(ft.Container(confirm_btn, margin=ft.margin.only(top=20)))
            
            self.result_display.content = ft.Column(steps, scroll=ft.ScrollMode.ALWAYS)
            self.page.update()
            
        except Exception as e:
            logger.error(f"Query processing error: {e}\n{traceback.format_exc()}")
            self.show_error(
                "Query Processing Failed",
                f"Exception: {str(e)}\n\nStack Trace:\n{traceback.format_exc()}"
            )
            self.add_status_bubble("System", "Error occurred", color="red")

    def execute_plan(self, query):
        try:
            self.add_status_bubble("Swarm", "Executing tasks...")
            results = self.orchestrator.run(query)
            
            if not results:
                self.show_error("Execution Failed", "No results returned from agents. Check logs for details.")
                return
            
            res_view = [ft.Text("Execution Finished", weight="bold", size=16), ft.Divider()]
            has_errors = False
            
            for res in results:
                result_text = str(res.get('result', 'No result'))
                is_err = "Error" in result_text or "error" in result_text.lower()
                
                if is_err:
                    has_errors = True
                
                res_view.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(
                                ft.icons.ERROR if is_err else ft.icons.CHECK_CIRCLE,
                                color="#D32F2F" if is_err else self.theme_color,
                                size=20
                            ),
                            ft.Text(f"Step {res['step']}", size=12, weight="bold", color=self.theme_color)
                        ]),
                        ft.Text(result_text, size=14, selectable=True)
                    ]),
                    bgcolor="#14171F" if not is_err else "#331111",
                    padding=10,
                    border_radius=8,
                    margin=ft.margin.only(bottom=5),
                    border=ft.border.all(1, "#D32F2F" if is_err else "#2A2E3D")
                ))
            
            self.result_display.content = ft.Column(res_view, scroll=ft.ScrollMode.ALWAYS)
            
            if has_errors:
                self.add_status_bubble("System", "Completed with errors", color="orange")
            else:
                self.add_status_bubble("System", "All tasks completed", color="green")
            
            self.page.update()
            
        except Exception as e:
            logger.error(f"Execution error: {e}\n{traceback.format_exc()}")
            self.show_error(
                "Execution Failed",
                f"Exception during agent execution: {str(e)}\n\nStack Trace:\n{traceback.format_exc()}"
            )
            self.add_status_bubble("System", "Execution failed", color="red")

    def run_workflow_ui(self, name):
        try:
            self.tabs.selected_index = 0
            self.tabs.on_change(None)
            self.add_status_bubble("Workflow", f"Started: {name}")
            
            results = self.workflow_engine.execute_workflow(name)
            
            if not results:
                self.show_error("Workflow Failed", f"No results from workflow '{name}'. Check if the workflow file is valid.")
                return
            
            res_view = [ft.Text(f"Workflow Complete: {name}", weight="bold", size=16), ft.Divider()]
            
            for res in results:
                if "error" in res:
                    res_view.append(ft.Container(
                        content=ft.Text(f"❌ {res.get('error', 'Unknown error')}", color="#D32F2F"),
                        bgcolor="#331111",
                        padding=10,
                        border_radius=8,
                        margin=ft.margin.only(bottom=5)
                    ))
                else:
                    res_view.append(ft.Text(f"✅ {res.get('result', 'No result')}", size=14))
            
            self.result_display.content = ft.Column(res_view, scroll=ft.ScrollMode.ALWAYS)
            self.page.update()
            
        except Exception as e:
            logger.error(f"Workflow execution error: {e}\n{traceback.format_exc()}")
            self.show_error(
                f"Workflow '{name}' Failed",
                f"Exception: {str(e)}\n\nStack Trace:\n{traceback.format_exc()}"
            )

def start_gui(orchestrator, workflow_engine):
    try:
        app = LIAApp(orchestrator, workflow_engine)
        ft.app(target=app.main)
    except Exception as e:
        logger.error(f"GUI startup failed: {e}\n{traceback.format_exc()}")
        print(f"FATAL ERROR: Could not start GUI\n{e}")
