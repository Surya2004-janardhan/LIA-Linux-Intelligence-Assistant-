import psutil
from agents.base_agent import LIAAgent
from core.logger import logger
from core.os_layer import os_layer
from core.errors import LIAResult, ErrorCode

class SysAgent(LIAAgent):
    def __init__(self):
        super().__init__("SysAgent", ["Process management", "Service control", "Health monitoring", "Disk status"])
        
        self.register_tool("check_cpu", self.check_cpu, "Returns current CPU usage",
            keywords=["cpu", "processor"])
        self.register_tool("check_ram", self.check_ram, "Returns current RAM usage",
            keywords=["ram", "memory usage", "memory"])
        self.register_tool("check_disk", self.check_disk, "Returns disk usage",
            keywords=["disk", "storage", "space"])
        self.register_tool("manage_service", self.manage_service, "Manage system services",
            keywords=["service", "systemctl", "restart", "start service", "stop service"])
        self.register_tool("system_health", self.system_health, "Full system health check",
            keywords=["health", "system status", "overview", "check system", "system info"])
        self.register_tool("list_processes", self.list_processes, "List top processes by resource usage",
            keywords=["process", "top", "running", "what's running", "task manager"])

    def check_cpu(self) -> str:
        usage = psutil.cpu_percent(interval=1)
        count = psutil.cpu_count()
        freq = psutil.cpu_freq()
        freq_str = f"{freq.current:.0f}MHz" if freq else "N/A"
        
        # Load average (Linux/Mac only)
        if hasattr(os_layer, 'is_linux') and (os_layer.is_linux or os_layer.is_mac):
            try:
                load = psutil.getloadavg()
                return f"CPU: {usage}% | Cores: {count} | Freq: {freq_str} | Load: {load[0]:.1f}/{load[1]:.1f}/{load[2]:.1f}"
            except Exception:
                pass
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
        """Combined health check — saves 3+ LLM calls."""
        info = os_layer.get_system_summary()
        cpu = self.check_cpu()
        ram = self.check_ram()
        disk = self.check_disk()
        
        return (f"╔══ System Health ══╗\n"
                f"Host: {info['hostname']} ({info['platform']}/{info['arch']})\n"
                f"Python: {info['python']}\n"
                f"─────────────────────\n"
                f"{cpu}\n{ram}\n{disk}\n"
                f"╚════════════════════╝")

    def list_processes(self, count: int = 10) -> str:
        """List top processes by CPU usage."""
        try:
            procs = []
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = p.info
                    procs.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by CPU usage
            procs.sort(key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)
            top = procs[:count]
            
            lines = [f"{'PID':<8} {'CPU%':<7} {'MEM%':<7} {'Name'}"]
            lines.append("─" * 40)
            for p in top:
                lines.append(f"{p['pid']:<8} {(p.get('cpu_percent') or 0):<7.1f} {(p.get('memory_percent') or 0):<7.1f} {p.get('name', '?')}")
            return "\n".join(lines)
        except Exception as e:
            return str(LIAResult.fail(ErrorCode.AGENT_CRASHED, f"Process listing failed: {e}"))

    def manage_service(self, service_name: str, action: str = "status") -> str:
        cmd = os_layer.get_service_cmd(service_name, action)
        if cmd is None:
            return str(LIAResult.fail(ErrorCode.SERVICE_UNAVAILABLE, 
                "Service management not supported on this platform"))
        
        result = os_layer.run_command(cmd, timeout=15)
        if result["success"]:
            return result["stdout"]
        return str(LIAResult.fail(
            ErrorCode.COMMAND_TIMEOUT if result["timed_out"] else ErrorCode.SERVICE_UNAVAILABLE,
            result["stderr"]
        ))

    def execute(self, task: str) -> str:
        logger.info(f"SysAgent executing: {task}")
        return self.smart_execute(task)
