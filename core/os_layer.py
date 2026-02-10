"""
LIA OS Layer — Linux-First Abstraction (Async).

This module provides deep Linux integration:
1. Distro detection via /etc/os-release
2. Kernel version via uname -r
3. System load via /proc/loadavg
4. Signal handling & process management
5. Safety Guard integration
6. ASYNC I/O for true concurrency
"""
import os
import sys
import signal
import platform
import asyncio
import threading
from typing import Optional, Callable, List, Union, Dict
from core.logger import logger

# Lazy import
_safety_guard = None

def get_safety_guard():
    global _safety_guard
    if _safety_guard is None:
        from core.safety import safety_guard
        _safety_guard = safety_guard
    return _safety_guard


class OSLayer:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.platform = platform.system().lower()
        self.is_linux = self.platform == "linux"
        self.is_mac = self.platform == "darwin"
        self.is_windows = self.platform == "windows"
        
        self.arch = platform.machine()
        self.hostname = platform.node()
        self.kernel = platform.release()
        self.distro = self._detect_distro() if self.is_linux else "N/A"
        self.python_version = platform.python_version()
        
        self._shutdown_hooks = []
        self._is_shutting_down = False
        
        self._register_signals()
        logger.info(f"OS Layer (Async): {self.distro} ({self.kernel}) on {self.arch}")

    def _detect_distro(self) -> str:
        try:
            with open("/etc/os-release") as f:
                data = {}
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        data[k] = v.strip('"')
            return f"{data.get('NAME', 'Linux')} {data.get('VERSION_ID', '')}"
        except Exception:
            return "Linux (Unknown Distro)"

    def _register_signals(self):
        try:
            signal.signal(signal.SIGINT, self._handle_shutdown)
            signal.signal(signal.SIGTERM, self._handle_shutdown)
        except (OSError, ValueError):
            pass

    def _handle_shutdown(self, signum, frame):
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        logger.info(f"Signal {signum} received. Shutting down...")
        
        # Run hooks
        for hook in self._shutdown_hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    # Attempt to schedule if loop is running, else standard calls
                    pass 
                else:
                    hook()
            except Exception:
                pass
        
        sys.exit(0)

    def register_shutdown_hook(self, hook: Callable):
        self._shutdown_hooks.append(hook)

    async def run_command(self, cmd: Union[List[str], str], timeout: int = 30, cwd: str = None, 
                          env: dict = None, shell: bool = False) -> Dict:
        """
        Async command execution.
        """
        import time
        start = time.monotonic()
        
        # Safety Check
        cmd_str = cmd if isinstance(cmd, str) else " ".join(cmd)
        guard = get_safety_guard()
        assessment = guard.validate_command(cmd_str)
        
        if assessment["risk_level"] == "BLOCKED":
            return {
                "success": False, "stdout": "", 
                "stderr": f"SAFETY BLOCK: {assessment['reason']}", 
                "returncode": -1, "duration_ms": 0, "timed_out": False
            }
        
        # Determine shell usage
        program = cmd
        args = []
        if isinstance(cmd, list):
            program = cmd[0]
            args = cmd[1:]
        
        if shell and isinstance(cmd, list):
            cmd = " ".join(cmd)
            
        # Prepare env
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
            
        try:
            if shell:
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=run_env
                )
            else:
                proc = await asyncio.create_subprocess_exec(
                    program, *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=run_env
                )
            
            try:
                stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                stdout = stdout_data.decode().strip() if stdout_data else ""
                stderr = stderr_data.decode().strip() if stderr_data else ""
                
                return {
                    "success": proc.returncode == 0,
                    "stdout": stdout,
                    "stderr": stderr,
                    "returncode": proc.returncode,
                    "duration_ms": int((time.monotonic() - start) * 1000),
                    "timed_out": False
                }
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                    await proc.communicate()
                except:
                    pass
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": f"TIMEOUT ({timeout}s)",
                    "returncode": -1,
                    "duration_ms": int((time.monotonic() - start) * 1000),
                    "timed_out": True
                }
                
        except Exception as e:
            return {
                "success": False, 
                "stdout": "", 
                "stderr": str(e), 
                "returncode": -1,
                "duration_ms": 0,
                "timed_out": False
            }

    # ─── LINUX SPECIFICS ──────────────────────────────────────────

    def get_load_avg(self) -> str:
        if self.is_linux:
            try:
                with open("/proc/loadavg") as f:
                    return f.read().strip()
            except Exception:
                pass
        return "N/A"

    def get_system_summary(self) -> dict:
        import psutil
        return {
            "platform": self.platform,
            "distro": self.distro,
            "kernel": self.kernel,
            "arch": self.arch,
            "hostname": self.hostname,
            "python": self.python_version,
            "load_avg": self.get_load_avg(),
            "cpu_count": psutil.cpu_count(),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1)
        }

    def get_package_manager(self) -> str:
        if self.is_linux:
            if os.path.exists("/usr/bin/apt-get"): return "apt"
            if os.path.exists("/usr/bin/dnf"): return "dnf"
            if os.path.exists("/usr/bin/pacman"): return "pacman"
            if os.path.exists("/usr/bin/zypper"): return "zypper"
        return "unknown"
    
    def get_service_cmd(self, service: str, action: str) -> Optional[List[str]]:
        if self.is_linux:
            return ["systemctl", action, service]
        return None

# Singleton
os_layer = OSLayer()
