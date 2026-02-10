import re
from agents.base_agent import LIAAgent
from core.logger import logger
from core.os_layer import os_layer
from core.errors import LIAResult, ErrorCode

class PackageAgent(LIAAgent):
    def __init__(self):
        super().__init__("PackageAgent", ["Package installation", "Updates", "Dependency management"])
        
        self.register_tool("install_pip", self.install_pip, "Installs a Python package via pip",
            keywords=["pip install", "python package", "pip"])
        self.register_tool("install_npm", self.install_npm, "Installs a Node package via npm",
            keywords=["npm install", "node package", "npm"])
        self.register_tool("list_pip", self.list_pip, "Lists installed pip packages",
            keywords=["pip list", "installed packages", "python packages"])
        self.register_tool("update_system", self.update_system, "Updates system packages",
            keywords=["update system", "apt update", "system update"])
        self.register_tool("check_outdated", self.check_outdated, "Shows outdated pip packages",
            keywords=["outdated", "upgrade", "old packages"])

    def install_pip(self, package_name: str) -> str:
        if not package_name or package_name.strip() == "":
            return str(LIAResult.fail(ErrorCode.INVALID_ARGS, "No package name provided"))
        result = os_layer.run_command(["pip", "install", package_name], timeout=120)
        if result["success"]:
            return f"✅ Installed: {package_name}\n{result['stdout'][-200:]}"
        return str(LIAResult.fail(ErrorCode.AGENT_CRASHED, 
            f"pip install {package_name} failed: {result['stderr'][-300:]}"))

    def install_npm(self, package_name: str) -> str:
        if not package_name or package_name.strip() == "":
            return str(LIAResult.fail(ErrorCode.INVALID_ARGS, "No package name provided"))
        result = os_layer.run_command(["npm", "install", "-g", package_name], timeout=120)
        if result["success"]:
            return f"✅ Installed: {package_name}"
        return str(LIAResult.fail(ErrorCode.AGENT_CRASHED,
            f"npm install {package_name} failed: {result['stderr'][-300:]}"))

    def list_pip(self) -> str:
        result = os_layer.run_command(["pip", "list", "--format=columns"], timeout=15)
        if result["success"]:
            return result["stdout"]
        return str(LIAResult.fail(ErrorCode.COMMAND_NOT_FOUND, result["stderr"]))

    def check_outdated(self) -> str:
        result = os_layer.run_command(["pip", "list", "--outdated", "--format=columns"], timeout=30)
        if result["success"]:
            return result["stdout"] if result["stdout"] else "All packages are up to date ✅"
        return str(LIAResult.fail(ErrorCode.COMMAND_NOT_FOUND, result["stderr"]))

    def update_system(self) -> str:
        if os_layer.is_windows:
            return str(LIAResult.fail(ErrorCode.SERVICE_UNAVAILABLE,
                "System package updates not supported on Windows via CLI",
                suggestion="Use Windows Update or winget manually"))
        
        pm = os_layer.get_package_manager()
        if pm == "apt":
            result = os_layer.run_command(["sudo", "apt", "update"], timeout=120)
        elif pm == "dnf":
            result = os_layer.run_command(["sudo", "dnf", "check-update"], timeout=120)
        elif pm == "brew":
            result = os_layer.run_command(["brew", "update"], timeout=120)
        else:
            return str(LIAResult.fail(ErrorCode.DEPENDENCY_MISSING, f"Unknown package manager: {pm}"))
        
        if result["success"]:
            return f"✅ System packages updated ({pm})\n{result['stdout'][-300:]}"
        return str(LIAResult.fail(ErrorCode.AGENT_CRASHED, result["stderr"][-300:]))

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        if tool_name in ("install_pip", "install_npm"):
            match = re.search(r'install\s+(\S+)', task, re.I)
            return {"package_name": match.group(1) if match else ""}
        return {}

    def execute(self, task: str) -> str:
        logger.info(f"PackageAgent executing: {task}")
        return self.smart_execute(task)
