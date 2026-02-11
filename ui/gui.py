import flet as ft
from core.logger import logger
from core.config import config
import traceback

class LIAApp:
    def __init__(self, orchestrator, workflow_engine):
        self.orchestrator = orchestrator
        self.workflow_engine = workflow_engine
        self.theme_color = "#00D2FF"

    async def main(self, page: ft.Page):
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
            ft.Switch(label="Enable Sandbox Ring (Linux Only)", value=config.get('security.sandbox_enabled')),
            ft.Switch(label="Strict Confirmation Mode", value=True),
            ft.Dropdown(
                label="Primary Model",
                value=config.get('llm.model'),
                options=[
                    ft.dropdown.Option("llama3"),
                    ft.dropdown.Option("mistral"),
                    ft.dropdown.Option("codellama"),
                ],
                width=300
            ),
            ft.ElevatedButton("Save Configuration", icon=ft.icons.SAVE, bgcolor=self.theme_color, color="white"),
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
        async def update_view(e):
            dashboard_content.visible = (self.tabs.selected_index == 0)
            settings_content.visible = (self.tabs.selected_index == 1)
            workflow_list.visible = (self.tabs.selected_index == 2)
            await page.update_async()
        
        self.tabs.on_change = update_view

        await page.add_async(
            self.tabs,
            ft.Divider(height=1, color="#2A2E3D"),
            ft.Stack([
                dashboard_content,
                settings_content,
                workflow_list
            ], expand=True)
        )

    async def show_error(self, message: str, details: str = None):
        """Displays error in both snackbar and result area."""
        self.error_snackbar.content.value = message
        self.error_snackbar.open = True
        
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
        await self.page.update_async()

    async def add_status_bubble(self, agent_name, status, color="#00D2FF"):
        bubble = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.CIRCLE, size=8, color=color),
                ft.Text(f"{agent_name}: {status}", size=11, color="#CCCCCC"),
            ]),
            padding=2,
        )
        self.status_feed.controls.insert(0, bubble)
        if len(self.status_feed.controls) > 50:
            self.status_feed.controls.pop()
        await self.page.update_async()

    async def process_query(self, query):
        if not query:
            await self.show_error("Empty Query", "Please enter a task or question for LIA.")
            return
        
        try:
            self.result_display.content = ft.Column([
                ft.ProgressBar(color=self.theme_color),
                ft.Text("Consulting Swarm...")
            ])
            await self.page.update_async()
            await self.add_status_bubble("Orchestrator", "Analyzing query...")
            
            # Start streaming from orchestrator
            async for update in self.orchestrator.run_stream(query):
                state = update.get("status")
                
                if state == "planning":
                    await self.add_status_bubble("Orchestrator", "Planning...")
                
                elif state == "planned":
                    plan = update["plan"]
                    steps_view = [ft.Text("Execution Plan Generated", weight="bold", size=16), ft.Divider()]
                    for step in plan.get('steps', []):
                        steps_view.append(ft.Row([
                            ft.Icon(ft.icons.PENDING_ACTIONS, size=16, color="#666666"),
                            ft.Text(f"[{step['agent']}] {step['task']}", size=14)
                        ]))
                    self.result_display.content = ft.Column(steps_view, scroll=ft.ScrollMode.ALWAYS)
                    await self.page.update_async()
                    await self.add_status_bubble("Swarm", "Plan ready")

                elif state == "executing":
                    await self.add_status_bubble(update['agent'], f"Working on: {update['task']}...")
                
                elif state == "completed":
                    await self.add_status_bubble(update['agent'], "Task completed", color="green")
                
                elif state == "error":
                    await self.add_status_bubble(update.get('agent', 'System'), "Error occurred", color="red")
                    if "step" not in update: # Fatal
                        await self.show_error("Execution Failed", update.get('message'))

                elif state == "finished":
                    results = update["results"]
                    res_view = [ft.Text("Execution Finished", weight="bold", size=16), ft.Divider()]
                    for res in results:
                        res_str = str(res['result'])
                        is_err = "Error" in res_str or "error" in res_str.lower()
                        res_view.append(ft.Container(
                            content=ft.Column([
                                ft.Text(f"Step {res['step']}", size=11, color=self.theme_color),
                                ft.Text(res_str, size=14, selectable=True)
                            ]),
                            bgcolor="#14171F" if not is_err else "#331111",
                            padding=10,
                            border_radius=8,
                            margin=ft.margin.only(bottom=5)
                        ))
                    self.result_display.content = ft.Column(res_view, scroll=ft.ScrollMode.ALWAYS)
                    await self.page.update_async()
                    await self.add_status_bubble("System", "All tasks finished", color="green")

        except Exception as e:
            logger.error(f"GUI Query Error: {e}\n{traceback.format_exc()}")
            await self.show_error("Query Processing Failed", str(e))

    async def run_workflow_ui(self, name):
        try:
            self.tabs.selected_index = 0
            await self.page.update_async()
            await self.add_status_bubble("Workflow", f"Started: {name}")
            
            # Workflow engine needs to be async-aligned as well, but for now we wrap in thread if sync
            results = await asyncio.to_thread(self.workflow_engine.execute_workflow, name)
            
            res_view = [ft.Text(f"Workflow Complete: {name}", weight="bold", size=16), ft.Divider()]
            for res in results:
                symbol = "❌" if "error" in res else "✅"
                res_view.append(ft.Text(f"{symbol} {res.get('result') or res.get('error')}", size=14))
            
            self.result_display.content = ft.Column(res_view, scroll=ft.ScrollMode.ALWAYS)
            await self.page.update_async()
        except Exception as e:
            await self.show_error(f"Workflow '{name}' Failed", str(e))

def start_gui(orchestrator, workflow_engine):
    app = LIAApp(orchestrator, workflow_engine)
    ft.app(target=app.main)
