from agents.base_agent import LIAAgent
from core.logger import logger
from core.permissions import permission_manager

class ConnectionAgent(LIAAgent):
    """
    Agent for third-party integrations (Gmail, Calendar, Custom APIs).
    All connections are DISABLED by default and require explicit permission.
    """
    def __init__(self):
        super().__init__("ConnectionAgent", ["Email integration", "Calendar access", "Custom API bridges"])
        
        self.register_tool("check_gmail", self.check_gmail, "Returns recent email subjects",
            keywords=["email", "gmail", "inbox", "mail"])
        self.register_tool("send_draft", self.send_draft, "Creates a draft email",
            keywords=["draft", "compose", "write email", "send"])
        self.register_tool("check_calendar", self.check_calendar, "Shows upcoming events",
            keywords=["calendar", "events", "schedule", "meetings"])

    def check_gmail(self):
        if not permission_manager.is_connection_active("gmail"):
            return "Connection Disabled: Gmail integration is OFF. Enable it in Settings > Connections."
        return "[Mock] Recent emails: 1. Meeting at 3pm, 2. PR Review Request, 3. Newsletter"

    def send_draft(self, to: str = "", subject: str = "", body: str = ""):
        if not permission_manager.is_connection_active("gmail"):
            return "Connection Disabled: Gmail integration is OFF. Enable it in Settings > Connections."
        return f"[Mock] Draft created: To={to}, Subject={subject}"

    def check_calendar(self):
        if not permission_manager.is_connection_active("calendar"):
            return "Connection Disabled: Calendar integration is OFF. Enable it in Settings > Connections."
        return "[Mock] Upcoming: 1. Team Standup (10am), 2. Lunch (12pm), 3. Code Review (3pm)"

    def execute(self, task: str) -> str:
        logger.info(f"ConnectionAgent executing task: {task}")
        return self.smart_execute(task)
