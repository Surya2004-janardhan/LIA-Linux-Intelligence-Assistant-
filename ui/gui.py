import flet as ft
import time
import json
from core.logger import logger
from core.config import config

class LIAApp:
    def __init__(self, orchestrator, workflow_engine):
        self.orchestrator = orchestrator
        self.workflow_engine = workflow_engine

    def main(self, page: ft.Page):
        self.page = page
        page.title = "LIA - Linux Intelligence Assistant"
        page.theme_mode = ft.ThemeMode.DARK
        page.window_width = 900
        page.window_height = 700
        page.padding = 30
        page.bgcolor = "#0F1117"  # Deep dark background
        
        # --- UI COMPONENTS ---
        
        # 1. Header
        header = ft.Row(
            [
                ft.Icon(ft.icons.PSYCHOLOGY, color="#00D2FF", size=40),
                ft.Text("LIA", size=32, weight="bold", color="#FFFFFF"),
                ft.Text(" Intelligence Assistant", size=24, color="#AAAAAA"),
            ],
            alignment=ft.MainAxisAlignment.START,
        )

        # 2. Input Section (Spotlight Style)
        search_field = ft.TextField(
            hint_text="English → Linux → Agents → Done. (100% Local)",
            expand=True,
            border_radius=15,
            bgcolor="#1A1D26",
            border_color="#2A2E3D",
            cursor_color="#00D2FF",
            on_submit=lambda e: self.process_query(e.control.value),
            prefix_icon=ft.icons.SEARCH,
        )

        execute_btn = ft.ElevatedButton(
            "Execute", 
            icon=ft.icons.ROCKET_LAUNCH,
            on_click=lambda _: self.process_query(search_field.value),
            style=ft.ButtonStyle(
                color="#FFFFFF",
                bgcolor="#00D2FF",
                shape=ft.RoundedRectangleBorder(radius=10)
            )
        )

        # 3. Agent Status Feed (Dynamic Bubbles)
        self.status_feed = ft.Column(
            expand=True,
            scroll=ft.ScrollMode.ALWAYS,
            spacing=10
        )

        # 4. Result Area (Rich Text)
        self.result_display = ft.Container(
            content=ft.Text("Results will appear here...", color="#666666"),
            bgcolor="#1A1D26",
            padding=20,
            border_radius=15,
            expand=2,
        )

        # 5. Workflow Shortcuts Sidebar
        workflow_chips = []
        for wf in self.workflow_engine.list_workflows():
            workflow_chips.append(
                ft.ActionChip(
                    label=ft.Text(wf.replace('_', ' ').capitalize()),
                    leading=ft.Icon(ft.icons.AUTO_FIX_HIGH),
                    on_click=lambda _, name=wf: self.run_workflow_ui(name)
                )
            )

        sidebar = ft.Column(
            [
                ft.Text("Workflows", size=18, weight="bold", color="#AAAAAA"),
                ft.Row(workflow_chips, wrap=True, spacing=10),
                ft.Divider(color="#2A2E3D"),
                ft.Text("Agent Status", size=18, weight="bold", color="#AAAAAA"),
                self.status_feed
            ],
            width=250,
        )

        # Main Layout
        page.add(
            header,
            ft.Divider(color="#2A2E3D"),
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Row([search_field, execute_btn]),
                            self.result_display,
                        ],
                        expand=3,
                    ),
                    ft.VerticalDivider(color="#2A2E3D"),
                    sidebar,
                ],
                expand=True,
            ),
        )

    def add_status_bubble(self, agent_name, status, color="#00D2FF"):
        bubble = ft.Container(
            content=ft.Row(
                [
                    ft.Icon(ft.icons.CIRCLE, size=10, color=color),
                    ft.Text(f"{agent_name}: {status}", size=12),
                ]
            ),
            padding=5,
        )
        self.status_feed.controls.insert(0, bubble)
        self.page.update()

    def process_query(self, query):
        if not query: return
        
        self.result_display.content = ft.Column([ft.ProgressRing(), ft.Text("Orchestrating plan...")])
        self.page.update()
        
        self.add_status_bubble("Orchestrator", "Analyzing query...")
        plan = self.orchestrator.plan(query)
        
        if "error" in plan:
            self.result_display.content = ft.Text(f"Error: {plan['error']}", color="red")
            self.page.update()
            return

        # Show the plan steps in status
        steps_display = []
        for step in plan.get('steps', []):
            steps_display.append(ft.Text(f"Step {step['id']}: [{step['agent']}] {step['task']}", size=14))
        
        steps_display.append(ft.Divider())
        self.result_display.content = ft.Column(steps_display)
        self.page.update()

        # Final Confirmation Button in result area
        confirm_btn = ft.ElevatedButton(
            "Confirm Execution", 
            on_click=lambda _: self.execute_plan(query),
            bgcolor="green",
            color="white"
        )
        self.result_display.content.controls.append(confirm_btn)
        self.page.update()

    def execute_plan(self, query):
        self.add_status_bubble("Orchestrator", "Executing plan...")
        results = self.orchestrator.run(query)
        
        res_texts = [ft.Text("Execution Results:", size=18, weight="bold")]
        for res in results:
            agent_color = "green" if "Error" not in str(res['result']) else "red"
            res_texts.append(ft.Text(f"Step {res['step']}: {res['result']}", color=agent_color))
        
        self.result_display.content = ft.Column(res_texts, scroll=ft.ScrollMode.ALWAYS)
        self.add_status_bubble("All Agents", "Tasks completed.", color="green")
        self.page.update()

    def run_workflow_ui(self, name):
        self.add_status_bubble("WorkflowEngine", f"Running {name}...")
        results = self.workflow_engine.execute_workflow(name)
        
        res_texts = [ft.Text(f"Workflow: {name}", size=18, weight="bold")]
        for res in results:
            res_texts.append(ft.Text(f"Step {res['step']}: {res['result']}"))
        
        self.result_display.content = ft.Column(res_texts, scroll=ft.ScrollMode.ALWAYS)
        self.page.update()

def start_gui(orchestrator, workflow_engine):
    app = LIAApp(orchestrator, workflow_engine)
    ft.app(target=app.main)
