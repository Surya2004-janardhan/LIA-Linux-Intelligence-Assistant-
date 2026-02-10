import subprocess
from agents.base_agent import LIAAgent
from core.logger import logger

class GitAgent(LIAAgent):
    def __init__(self):
        super().__init__("GitAgent", ["Version control", "Commits", "PR management", "Repo status"])
        
        self.register_tool("git_status", self.git_status, "Checks the current git status",
            keywords=["status", "changes", "modified", "staged"])
        self.register_tool("git_commit", self.git_commit, "Stages and commits with a message",
            keywords=["commit"])
        self.register_tool("gh_pr_list", self.gh_pr_list, "Lists open pull requests",
            keywords=["pull request", "pr", "merge request"])
        self.register_tool("git_log", self.git_log, "Shows recent commit history",
            keywords=["log", "history", "recent commits"])
        self.register_tool("git_diff", self.git_diff, "Shows uncommitted changes",
            keywords=["diff", "what changed"])

    def _run_command(self, cmd: list, timeout: int = 15):
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
        except subprocess.TimeoutExpired:
            return f"Timeout: {' '.join(cmd)} took too long."
        except FileNotFoundError:
            return f"Error: '{cmd[0]}' not found. Is it installed?"
        except Exception as e:
            return f"Command failure: {str(e)}"

    def git_status(self):
        return self._run_command(['git', 'status', '--short'])

    def git_commit(self, message: str = "Auto-commit by LIA"):
        self._run_command(['git', 'add', '.'])
        return self._run_command(['git', 'commit', '-m', message])

    def git_log(self, count: int = 10):
        return self._run_command(['git', 'log', f'--oneline', f'-n', str(count)])

    def git_diff(self):
        return self._run_command(['git', 'diff', '--stat'])

    def gh_pr_list(self):
        return self._run_command(['gh', 'pr', 'list'])

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        import re
        if tool_name == "git_commit":
            match = re.search(r"(?:message|msg|with)\s+['\"](.+?)['\"]", task, re.I)
            if match:
                return {"message": match.group(1)}
            # Try extracting text after "commit"
            match = re.search(r"commit\s+(.+)", task, re.I)
            return {"message": match.group(1).strip() if match else "Auto-commit by LIA"}
        return {}

    def execute(self, task: str) -> str:
        logger.info(f"GitAgent executing task: {task}")
        return self.smart_execute(task)
