import webbrowser
from agents.base_agent import LIAAgent
from core.logger import logger
from core.llm_bridge import llm_bridge

class WebAgent(LIAAgent):
    def __init__(self):
        super().__init__("WebAgent", ["Web search", "Deep linking", "Open browser", "Send notifications"])
        self.register_tool("open_url", self.open_url, "Opens a URL in the default web browser")
        self.register_tool("google_search", self.google_search, "Performs a Google search in the browser")

    def open_url(self, url: str):
        try:
            webbrowser.open(url)
            return f"Opened {url} in browser."
        except Exception as e:
            return f"Error: {str(e)}"

    def google_search(self, query: str):
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        return self.open_url(url)

    def execute(self, task: str) -> str:
        logger.info(f"WebAgent executing task: {task}")
        prompt = f"{self.get_capabilities_prompt()}\n\nUser Task: {task}\n\nDecide tool and args in JSON:"
        messages = [{"role": "system", "content": "You are a Web navigation specialist."}, {"role": "user", "content": prompt}]
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
            return f"WebAgent failed: {str(e)}"
