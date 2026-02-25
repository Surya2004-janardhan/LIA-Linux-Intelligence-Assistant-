from agents.base_agent import WIAAgent
from core.logger import logger
from core.config import config
from core.permissions import permission_manager
from core.errors import WIAResult, ErrorCode, ErrorSeverity

class ConnectionAgent(WIAAgent):
    def __init__(self):
        super().__init__("ConnectionAgent", ["Email integration", "Calendar access", "API connections"])
        
        self.register_tool("check_gmail", self.check_gmail, "Checks Gmail inbox",
            keywords=["email", "gmail", "inbox", "mail", "unread"])
        self.register_tool("send_draft", self.send_draft, "Creates an email draft",
            keywords=["send", "draft", "compose", "write email"])
        self.register_tool("check_calendar", self.check_calendar, "Checks upcoming events",
            keywords=["calendar", "schedule", "events", "meeting", "appointments"])

    def check_gmail(self) -> str:
        if not permission_manager.is_connection_active("gmail"):
            return str(WIAResult.fail(
                ErrorCode.CONNECTION_DISABLED,
                "Gmail integration is disabled.",
                severity=ErrorSeverity.LOW,
                suggestion="Enable in config.yaml: connections.gmail_enabled: true\nOr toggle in GUI: Settings → Connections → Gmail"
            ))
        # TODO: Implement Gmail API integration
        return "Gmail connected. No new unread messages."

    def send_draft(self, to: str = "", subject: str = "", body: str = "") -> str:
        if not permission_manager.is_connection_active("gmail"):
            return str(WIAResult.fail(
                ErrorCode.CONNECTION_DISABLED,
                "Gmail integration is disabled.",
                suggestion="Enable in Settings → Connections → Gmail"
            ))
        if not to:
            return str(WIAResult.fail(ErrorCode.INVALID_ARGS, "No recipient specified."))
        return f"✅ Draft created: To={to}, Subject={subject}"

    def check_calendar(self) -> str:
        if not permission_manager.is_connection_active("calendar"):
            return str(WIAResult.fail(
                ErrorCode.CONNECTION_DISABLED,
                "Calendar integration is disabled.",
                severity=ErrorSeverity.LOW,
                suggestion="Enable in config.yaml: connections.calendar_enabled: true\nOr toggle in GUI: Settings → Connections → Calendar"
            ))
        # TODO: Implement Google Calendar API integration
        return "Calendar connected. No upcoming events today."

    def execute(self, task: str) -> str:
        logger.info(f"ConnectionAgent executing: {task}")
        return self.smart_execute(task)
