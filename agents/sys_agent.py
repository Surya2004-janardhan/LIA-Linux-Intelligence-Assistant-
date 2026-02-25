import psutil
import shlex
from agents.base_agent import WIAAgent
from core.logger import logger
from core.os_layer import os_layer
from core.errors import WIAResult, ErrorCode

class SysAgent(WIAAgent):
    def __init__(self):
        super().__init__("SysAgent", ["Process management", "Service control", "Health monitoring", "Disk status"])
        
        self.register_tool("check_cpu", self.check_cpu, "Returns current CPU usage",
            keywords=["cpu", "processor", "load"])
        self.register_tool("check_ram", self.check_ram, "Returns current RAM usage",
            keywords=["ram", "memory usage", "memory"])
        self.register_tool("check_disk", self.check_disk, "Returns disk usage",
            keywords=["disk", "storage", "space", "partition"])
        self.register_tool("manage_service", self.manage_service, "Manage system services",
            keywords=["service", "systemctl", "restart", "start service", "stop service"])
        self.register_tool("system_health", self.system_health, "Full system health check",
            keywords=["health", "system status", "overview", "check system", "system info"])
        self.register_tool("list_processes", self.list_processes, "List top processes by resource usage",
            keywords=["process", "top", "running", "what's running", "task manager"])
        self.register_tool("check_logs", self.check_logs, "Check system journals",
            keywords=["logs", "journal", "error log", "syslog"])

    def check_cpu(self) -> str:
        usage = psutil.cpu_percent(interval=1)
        count = psutil.cpu_count()
        freq = psutil.cpu_freq()
        freq_str = f"{freq.current:.0f}MHz" if freq else "N/A"
        
        return f"CPU: {usage}% | Cores: {count} | Freq: {freq_str}"

    def check_ram(self) -> str:
        ram = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return (f"RAM: {ram.percent}% ({ram.used // (1024**2)}MB / {ram.total // (1024**2)}MB)\n"
                f"Swap: {swap.percent}% ({swap.used // (1024**2)}MB / {swap.total // (1024**2)}MB)")

    def check_disk(self) -> str:
        partitions = psutil.disk_partitions()
        results = []
        for p in partitions:
            try:
                usage = psutil.disk_usage(p.mountpoint)
                free_gb = usage.free / (1024**3)
                total_gb = usage.total / (1024**3)
                results.append(f"{p.mountpoint}: {usage.percent}% used ({free_gb:.1f}GB free / {total_gb:.1f}GB total)")
            except (PermissionError, OSError):
                continue
        return "\n".join(results) if results else "Could not read disk info."

    def system_health(self) -> str:
        """Combined health check for Windows."""
        info = os_layer.get_system_summary()
        cpu = self.check_cpu()
        ram = self.check_ram()
        disk = self.check_disk()
        
        return (f"╔══ System Health (WIA) ══╗\n"
                f"Host: {info['hostname']} ({info['os_version']})\n"
                f"Kernel: {info['kernel']}\n"
                f"─────────────────────\n"
                f"{cpu}\n{ram}\n{disk}\n"
                f"╚════════════════════╝")

    def list_processes(self, count: int = 10) -> str:
        """List top processes by CPU usage on Windows."""
        try:
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = p.info
                    procs.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            procs.sort(key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)
            top = procs[:count]
            
            lines = [f"{'PID':<8} {'CPU%':<7} {'MEM%':<7} {'Name'}"]
            lines.append("─" * 40)
            for p in top:
                lines.append(f"{p['pid']:<8} {(p.get('cpu_percent') or 0):<7.1f} {(p.get('memory_percent') or 0):<7.1f} {p.get('name', '?')}")
            return "\n".join(lines)
        except Exception as e:
            return str(WIAResult.fail(ErrorCode.AGENT_CRASHED, f"Process listing failed: {e}"))

    def check_logs(self, service: str = "", limit: int = 50) -> str:
        """Reads Windows Event Logs via PowerShell."""
        if not os_layer.is_windows:
            return "Log checking is only supported on Windows in this build."
        
        # We use Get-WinEvent for performance, fallback to Get-EventLog
        if service:
            ps_cmd = f"Get-WinEvent -LogName System -MaxEvents {limit} | Where-Object {{ $_.ProviderName -like '*{service}*' }}"
        else:
            ps_cmd = f"Get-WinEvent -LogName System -MaxEvents {limit} -ErrorAction SilentlyContinue"
            
        result = asyncio.run(os_layer.run_command(ps_cmd, shell=True, timeout=10))
        if not result["success"]:
            # Try fallback if Get-WinEvent fails
            ps_cmd = f"Get-EventLog -LogName System -Newest {limit}"
            result = asyncio.run(os_layer.run_command(ps_cmd, shell=True, timeout=10))
            
        if not result["success"]:
            return f"❌ Failed to read Event Logs: {result['stderr']}"
        
        return f"📜 Windows Event Logs ({limit} events):\n{result['stdout']}"

    def manage_service(self, service_name: str, action: str = "status") -> str:
        """Manage Windows services via sc.exe or PowerShell."""
        cmd = os_layer.get_service_cmd(service_name, action)
        if cmd is None:
            # Special handling for restart on Windows
            if action == "restart":
                stop_res = asyncio.run(os_layer.run_command(["sc.exe", "stop", service_name], timeout=20))
                import time
                time.sleep(2) # Give it a moment to stop
                start_res = asyncio.run(os_layer.run_command(["sc.exe", "start", service_name], timeout=20))
                if start_res["success"]:
                    return f"Service '{service_name}' restarted successfully."
                return f"Failed to restart service: {start_res['stderr']}"
            
            return str(WIAResult.fail(ErrorCode.SERVICE_UNAVAILABLE, 
                "Service action not supported on this platform"))
        
        result = asyncio.run(os_layer.run_command(cmd, timeout=15))
        if result["success"]:
            return result["stdout"]
        return str(WIAResult.fail(
            ErrorCode.COMMAND_TIMEOUT if result["timed_out"] else ErrorCode.SERVICE_UNAVAILABLE,
            result["stderr"]
        ))

    async def execute(self, task: str) -> str:
        logger.info(f"SysAgent executing: {task}")
        # Add extract_args for check_logs
        import re
        if "log" in task.lower() or "event" in task.lower():
            match = re.search(r'(?:logs?|events?)\s+(?:for\s+|of\s+)?([a-zA-Z0-9\-_]+)', task, re.I)
            if match:
                service = match.group(1).strip()
                if service not in ["check", "show", "me", "recent", "error"]:
                    return self.check_logs(service=service)
            return self.check_logs()
            
        return await self.smart_execute(task)
