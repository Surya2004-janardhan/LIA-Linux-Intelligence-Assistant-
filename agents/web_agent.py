import webbrowser
import re
from agents.base_agent import LIAAgent
from core.logger import logger

class WebAgent(LIAAgent):
    def __init__(self):
        super().__init__("WebAgent", ["Web search", "Deep linking", "Open browser"])
        
        self.register_tool("open_url", self.open_url, "Opens a URL in the default browser",
            keywords=["open", "launch", "go to", "navigate", "visit"])
        self.register_tool("google_search", self.google_search, "Performs a Google search",
            keywords=["search", "google", "look up", "find online"])

    def open_url(self, url: str):
        # Ensure URL has protocol
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"
        try:
            webbrowser.open(url)
            return f"Opened {url} in browser."
        except Exception as e:
            return f"Error: {str(e)}"

    def google_search(self, query: str):
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        return self.open_url(url)

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        if tool_name == "open_url":
            # Extract URL from task
            match = re.search(r'(https?://\S+|www\.\S+|\S+\.\w{2,})', task)
            if match:
                return {"url": match.group(1)}
            return {}
        if tool_name == "google_search":
            match = re.search(r'(?:search|google)\s+(?:for\s+)?(.+)', task, re.I)
            return {"query": match.group(1).strip() if match else task}
        return {}

    def execute(self, task: str) -> str:
        logger.info(f"WebAgent executing task: {task}")
        return self.smart_execute(task)
