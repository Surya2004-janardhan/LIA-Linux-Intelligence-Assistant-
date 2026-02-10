import flet as ft
from core.logger import logger
from core.config import config

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

    def add_status_bubble(self, agent_name, status, color="#00D2FF"):
        bubble = ft.Container(
            content=ft.Row([
                ft.Icon(ft.icons.CIRCLE, size=8, color=color),
                ft.Text(f"{agent_name}: {status}", size=11, color="#CCCCCC"),
            ]),
            padding=2,
        )
        self.status_feed.controls.insert(0, bubble)
        self.page.update()

    def process_query(self, query):
        if not query: return
        self.result_display.content = ft.Column([ft.ProgressBar(color=self.theme_color), ft.Text("Consulting Swarm...")])
        self.page.update()
        
        self.add_status_bubble("Orchestrator", "Thinking...")
        plan = self.orchestrator.plan(query)
        
        if "error" in plan:
            self.result_display.content = ft.Text(f"Plan Error: {plan['error']}", color="red")
            self.page.update()
            return

        steps = [ft.Text("Execution Plan Generated", weight="bold", size=16), ft.Divider()]
        for step in plan.get('steps', []):
            steps.append(ft.Row([
                ft.Icon(ft.icons.CHECK_CIRCLE_OUTLINE, size=16, color=self.theme_color),
                ft.Text(f"[{step['agent']}] {step['task']}", size=14)
            ]))
        
        confirm_btn = ft.ElevatedButton("Start Swarm Execution", icon=ft.icons.PLAY_ARROW, on_click=lambda _: self.execute_plan(query), bgcolor=self.theme_color, color="white")
        steps.append(ft.Container(confirm_btn, margin=ft.margin.only(top=20)))
        
        self.result_display.content = ft.Column(steps, scroll=ft.ScrollMode.ALWAYS)
        self.page.update()

    def execute_plan(self, query):
        self.add_status_bubble("Swarm", "Executing tasks...")
        results = self.orchestrator.run(query)
        
        res_view = [ft.Text("Execution Finished", weight="bold", size=16), ft.Divider()]
        for res in results:
            is_err = "Error" in str(res['result'])
            res_view.append(ft.Container(
                content=ft.Column([
                    ft.Text(f"Step {res['step']}", size=12, weight="bold", color=self.theme_color),
                    ft.Text(str(res['result']), size=14)
                ]),
                bgcolor="#14171F" if not is_err else "#331111",
                padding=10,
                border_radius=8,
                margin=ft.margin.only(bottom=5)
            ))
        
        self.result_display.content = ft.Column(res_view, scroll=ft.ScrollMode.ALWAYS)
        self.add_status_bubble("System", "Ready.", color="green")
        self.page.update()

    def run_workflow_ui(self, name):
        self.tabs.selected_index = 0
        # Trigger visibility update manually
        self.tabs.on_change(None)
        self.add_status_bubble("Workflow", f"Started: {name}")
        results = self.workflow_engine.execute_workflow(name)
        
        res_view = [ft.Text(f"Workflow Complete: {name}", weight="bold", size=16), ft.Divider()]
        for res in results:
            res_view.append(ft.Text(f"• {res['result']}", size=14))
        
        self.result_display.content = ft.Column(res_view, scroll=ft.ScrollMode.ALWAYS)
        self.page.update()

def start_gui(orchestrator, workflow_engine):
    app = LIAApp(orchestrator, workflow_engine)
    ft.app(target=app.main)
