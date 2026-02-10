import psutil
import subprocess
import os
from agents.base_agent import LIAAgent
from core.logger import logger

class SysAgent(LIAAgent):
    def __init__(self):
        super().__init__("SysAgent", ["Process management", "Service control", "Health monitoring", "Disk status"])
        
        self.register_tool("check_cpu", self.check_cpu, "Returns current CPU usage percentage",
            keywords=["cpu", "processor"])
        self.register_tool("check_ram", self.check_ram, "Returns current RAM usage",
            keywords=["ram", "memory usage", "memory"])
        self.register_tool("check_disk", self.check_disk, "Returns disk usage for all partitions",
            keywords=["disk", "storage", "space"])
        self.register_tool("manage_service", self.manage_service, "Manage system services (Linux only)",
            keywords=["service", "systemctl", "restart", "start service", "stop service"])
        self.register_tool("system_health", self.system_health, "Full system health summary",
            keywords=["health", "system status", "overview", "check system"])

    def check_cpu(self):
        usage = psutil.cpu_percent(interval=1)
        count = psutil.cpu_count()
        freq = psutil.cpu_freq()
        return f"CPU: {usage}% | Cores: {count} | Freq: {freq.current:.0f}MHz"

    def check_ram(self):
        ram = psutil.virtual_memory()
        return f"RAM: {ram.percent}% ({ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB)"

    def check_disk(self):
        partitions = psutil.disk_partitions()
        results = []
        for p in partitions:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                results.append(f"{p.mountpoint}: {usage.percent}% used ({usage.free // (1024**3)}GB free)")
            except PermissionError:
                continue
        return "\n".join(results) if results else "Could not read disk info."

    def system_health(self):
        """Full system health in one call — saves 3 separate LLM calls."""
        cpu = self.check_cpu()
        ram = self.check_ram()
        disk = self.check_disk()
        return f"=== System Health ===\n{cpu}\n{ram}\n{disk}"

    def manage_service(self, service_name: str, action: str = "status"):
        if os.name == 'nt':
            return "Service management via systemctl is Linux only."
        try:
            result = subprocess.run(['systemctl', action, service_name], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return f"'{action}' on '{service_name}': {result.stdout}"
            return f"Failed: {result.stderr}"
        except subprocess.TimeoutExpired:
            return f"Timeout: systemctl {action} {service_name} took too long."
        except Exception as e:
            return f"Error: {str(e)}"

    def execute(self, task: str) -> str:
        logger.info(f"SysAgent executing task: {task}")
        return self.smart_execute(task)
