import re
from agents.base_agent import LIAAgent
from core.logger import logger
from core.os_layer import os_layer
from core.errors import LIAResult, ErrorCode

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
        self.register_tool("git_branch", self.git_branch, "Lists or shows current branch",
            keywords=["branch", "branches"])

    def git_status(self) -> str:
        result = os_layer.run_command(['git', 'status', '--short'], timeout=10)
        if not result["success"]:
            return str(LIAResult.fail(ErrorCode.COMMAND_NOT_FOUND, result["stderr"]))
        return result["stdout"] if result["stdout"] else "Working tree clean ✅"

    def git_commit(self, message: str = "Auto-commit by LIA") -> str:
        # Stage
        stage = os_layer.run_command(['git', 'add', '.'], timeout=10)
        if not stage["success"]:
            return str(LIAResult.fail(ErrorCode.COMMAND_NOT_FOUND, stage["stderr"]))
        # Commit
        result = os_layer.run_command(['git', 'commit', '-m', message], timeout=15)
        if not result["success"]:
            if "nothing to commit" in result["stderr"].lower() or "nothing to commit" in result["stdout"].lower():
                return "Nothing to commit — working tree clean."
            return str(LIAResult.fail(ErrorCode.AGENT_CRASHED, result["stderr"]))
        return f"✅ Committed: {message}\n{result['stdout']}"

    def git_log(self, count: int = 10) -> str:
        result = os_layer.run_command(['git', 'log', '--oneline', '-n', str(count)], timeout=10)
        if not result["success"]:
            return str(LIAResult.fail(ErrorCode.COMMAND_NOT_FOUND, result["stderr"]))
        return result["stdout"]

    def git_diff(self) -> str:
        result = os_layer.run_command(['git', 'diff', '--stat'], timeout=10)
        if not result["success"]:
            return str(LIAResult.fail(ErrorCode.COMMAND_NOT_FOUND, result["stderr"]))
        return result["stdout"] if result["stdout"] else "No uncommitted changes."

    def git_branch(self) -> str:
        result = os_layer.run_command(['git', 'branch', '-a'], timeout=10)
        if not result["success"]:
            return str(LIAResult.fail(ErrorCode.COMMAND_NOT_FOUND, result["stderr"]))
        return result["stdout"]

    def gh_pr_list(self) -> str:
        result = os_layer.run_command(['gh', 'pr', 'list'], timeout=15)
        if not result["success"]:
            if "not found" in result["stderr"].lower() or result["returncode"] == -1:
                return str(LIAResult.fail(ErrorCode.DEPENDENCY_MISSING, 
                    "GitHub CLI (gh) not found", suggestion="Install: https://cli.github.com"))
            return str(LIAResult.fail(ErrorCode.COMMAND_NOT_FOUND, result["stderr"]))
        return result["stdout"] if result["stdout"] else "No open pull requests."

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        if tool_name == "git_commit":
            match = re.search(r"(?:message|msg|with)\s+['\"](.+?)['\"]", task, re.I)
            if match:
                return {"message": match.group(1)}
            match = re.search(r"commit\s+(.+)", task, re.I)
            return {"message": match.group(1).strip() if match else "Auto-commit by LIA"}
        return {}

    def execute(self, task: str) -> str:
        logger.info(f"GitAgent executing: {task}")
        return self.smart_execute(task)
