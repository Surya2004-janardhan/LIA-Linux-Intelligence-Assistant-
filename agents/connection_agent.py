from agents.base_agent import LIAAgent
from core.logger import logger
from core.llm_bridge import llm_bridge
from core.permissions import permission_manager

class ConnectionAgent(LIAAgent):
    """
    Agent responsible for 3rd party integrations (Gmail, Calendar, etc.)
    Only executes if the connection is explicitly enabled in settings.
    """
    def __init__(self):
        super().__init__("ConnectionAgent", ["Gmail access", "Calendar management", "External API bridge"])
        self.register_tool("check_gmail", self.check_gmail, "Returns recent email subjects (Requires Enablement)")
        self.register_tool("send_draft", self.send_draft, "Creates an email draft")

    def check_gmail(self):
        if not permission_manager.is_connection_active("gmail"):
            return "Connection Error: Gmail integration is DISABLED in security settings."
        
        # In a real implementation, we would use google-api-python-client
        return "Gmail (MOCK-PROXIED): You have 3 new messages regarding 'Project LIA'."

    def send_draft(self, recipient: str, subject: str, body: str):
        if not permission_manager.is_connection_active("gmail"):
            return "Connection Error: Gmail integration is DISABLED."
            
        return f"DRAFT CREATED: To: {recipient} | Subject: {subject}"

    def execute(self, task: str) -> str:
        logger.info(f"ConnectionAgent checking task: {task}")
        prompt = f"{self.get_capabilities_prompt()}\n\nTask: {task}\n\nJSON output:"
        messages = [{"role": "system", "content": "You manage 3rd party connections."}, {"role": "user", "content": prompt}]
        
        try:
            import json
            response = llm_bridge.generate(messages, response_format={"type": "json_object"})
            data = json.loads(response)
            tool_name = data.get("tool")
            args = data.get("args", {})
            
            if tool_name in self.tools:
                return self.tools[tool_name]["func"](**args)
            return f"Error: Tool {tool_name} not found."
        except Exception as e:
            return f"ConnectionAgent fail: {str(e)}"
