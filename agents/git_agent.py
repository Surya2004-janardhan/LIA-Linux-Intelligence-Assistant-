import subprocess
from agents.base_agent import LIAAgent
from core.logger import logger
from core.llm_bridge import llm_bridge

class GitAgent(LIAAgent):
    def __init__(self):
        super().__init__("GitAgent", ["Version control", "Commits", "PR management", "Repo status"])
        self.register_tool("git_status", self.git_status, "Checks the current git status")
        self.register_tool("git_commit", self.git_commit, "Stages all changes and commits with a message")
        self.register_tool("gh_pr_list", self.gh_pr_list, "Lists open pull requests using GitHub CLI")

    def _run_command(self, cmd: list):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return f"Success:\n{result.stdout}"
            else:
                return f"Error:\n{result.stderr}"
        except Exception as e:
            return f"Command failure: {str(e)}"

    def git_status(self):
        return self._run_command(['git', 'status'])

    def git_commit(self, message: str):
        # Stage all, then commit
        self._run_command(['git', 'add', '.'])
        return self._run_command(['git', 'commit', '-m', message])

    def gh_pr_list(self):
        return self._run_command(['gh', 'pr', 'list'])

    def execute(self, task: str) -> str:
        logger.info(f"GitAgent executing task: {task}")
        prompt = f"{self.get_capabilities_prompt()}\n\nUser Task: {task}\n\nDecide tool and args in JSON:"
        messages = [{"role": "system", "content": "You are a Git specialist."}, {"role": "user", "content": prompt}]
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
            return f"GitAgent failed: {str(e)}"
