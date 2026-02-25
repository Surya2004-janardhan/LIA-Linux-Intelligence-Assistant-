import re
import webbrowser
from agents.base_agent import WIAAgent
from core.logger import logger
from core.errors import WIAResult, ErrorCode

class WebAgent(WIAAgent):
    def __init__(self):
        super().__init__("WebAgent", ["Web browsing", "URL opening", "Google search"])
        
        self.register_tool("open_url", self.open_url, "Opens a URL in the default browser",
            keywords=["open", "launch", "visit", "browse", "go to", "navigate"])
        self.register_tool("google_search", self.google_search, "Opens a Google search",
            keywords=["search", "google", "look up", "find online"])

    def open_url(self, url: str) -> str:
        if not url or not url.strip():
            return str(WIAResult.fail(ErrorCode.INVALID_ARGS, "No URL provided"))
        
        # Auto-prefix protocol
        url = url.strip()
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        
        try:
            webbrowser.open(url)
            return f"✅ Opened: {url}"
        except Exception as e:
            return str(WIAResult.fail(ErrorCode.AGENT_CRASHED, f"Failed to open browser: {e}"))

    def google_search(self, query: str) -> str:
        if not query or not query.strip():
            return str(WIAResult.fail(ErrorCode.INVALID_ARGS, "No search query provided"))
        
        import urllib.parse
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={encoded}"
        try:
            webbrowser.open(url)
            return f"✅ Searching Google for: {query}"
        except Exception as e:
            return str(WIAResult.fail(ErrorCode.AGENT_CRASHED, f"Failed to open browser: {e}"))

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        if tool_name == "open_url":
            # Extract URL from task
            match = re.search(r'(https?://\S+|www\.\S+|\S+\.\w{2,}(?:/\S*)?)', task, re.I)
            return {"url": match.group(1) if match else ""}
        if tool_name == "google_search":
            # Extract everything after "search for" or "google"
            match = re.search(r'(?:search\s+(?:for\s+)?|google\s+)(.+)', task, re.I)
            return {"query": match.group(1).strip() if match else task}
        return {}

    def execute(self, task: str) -> str:
        logger.info(f"WebAgent executing: {task}")
        return self.smart_execute(task)
