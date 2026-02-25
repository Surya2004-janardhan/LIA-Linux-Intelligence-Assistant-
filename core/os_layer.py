"""
WIA OS Layer — Windows-First Abstraction (Async).

This module provides deep Windows integration:
1. Windows version and build detection
2. PowerShell-first command execution
3. System resource monitoring via psutil
4. Service management via sc.exe
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
        self.is_windows = self.platform == "windows"
        self.is_linux = self.platform == "linux"
        self.is_mac = self.platform == "darwin"
        
        self.arch = platform.machine()
        self.hostname = platform.node()
        self.kernel = platform.release()
        self.os_version = self._detect_os_version()
        self.python_version = platform.python_version()
        
        self._shutdown_hooks = []
        self._is_shutting_down = False
        
        self._register_signals()
        logger.info(f"OS Layer (Async): {self.os_version} ({self.kernel}) on {self.arch}")

    def _detect_os_version(self) -> str:
        if self.is_windows:
            try:
                import winrun
                # Fallback to platform if winrun not available
                return f"Windows {platform.release()} (Build {platform.version()})"
            except ImportError:
                return f"Windows {platform.release()} ({platform.version()})"
        elif self.is_linux:
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
        return f"{self.platform.capitalize()} {platform.release()}"

    def _register_signals(self):
        try:
            # On Windows, only a few signals are supported
            if hasattr(signal, 'SIGINT'):
                signal.signal(signal.SIGINT, self._handle_shutdown)
            if hasattr(signal, 'SIGTERM'):
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
                    pass 
                else:
                    hook()
            except Exception:
                pass
        
        sys.exit(0)

    def register_shutdown_hook(self, hook: Callable):
        self._shutdown_hooks.append(hook)

    async def run_command(self, cmd: Union[List[str], str], timeout: int = 30, cwd: str = None, 
                          env: dict = None, shell: bool = False, sandbox: bool = False) -> Dict:
        """
        Async command execution optimized for Windows.
        """
        import time
        from core.sandbox import sandbox as sandbox_ring
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
        
        # Apply Sandboxing if requested
        if sandbox and self.is_linux:
            if isinstance(cmd, str):
                if not shell:
                    cmd_list = cmd.split()
                    cmd = sandbox_ring.wrap_command(cmd_list)
                else:
                    cmd = f"firejail --quiet --net=none --private -- {cmd}"
            else:
                cmd = sandbox_ring.wrap_command(cmd)
        elif sandbox and self.is_windows:
            logger.warning("Sandboxing not yet fully implemented for Windows. Running unisolated.")

        # Prepare env
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
            
        try:
            if shell:
                # On Windows, we prefer PowerShell for complex tasks
                if self.is_windows and not cmd_str.startswith("powershell"):
                    cmd = f"powershell -NoProfile -ExecutionPolicy Bypass -Command \"{cmd_str.replace('\"', '\\\"')}\""
                
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=run_env
                )
            else:
                if isinstance(cmd, str):
                    cmd = cmd.split()
                
                program = cmd[0]
                args = cmd[1:]
                
                proc = await asyncio.create_subprocess_exec(
                    program, *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=cwd,
                    env=run_env
                )
            
            try:
                stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=timeout)
                stdout = stdout_data.decode('utf-8', errors='replace').strip() if stdout_data else ""
                stderr = stderr_data.decode('utf-8', errors='replace').strip() if stderr_data else ""
                
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
                    proc.terminate() # terminate is better on windows
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

    def get_system_summary(self) -> dict:
        import psutil
        return {
            "platform": self.platform,
            "os_version": self.os_version,
            "kernel": self.kernel,
            "arch": self.arch,
            "hostname": self.hostname,
            "python": self.python_version,
            "cpu_count": psutil.cpu_count(),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1)
        }

    def get_package_manager(self) -> str:
        if self.is_windows:
            if shutil.which("winget"): return "winget"
            if shutil.which("choco"): return "choco"
        elif self.is_linux:
            if os.path.exists("/usr/bin/apt-get"): return "apt"
            if os.path.exists("/usr/bin/pacman"): return "pacman"
        return "unknown"
    
    def get_service_cmd(self, service: str, action: str) -> Optional[List[str]]:
        if self.is_windows:
            # Map systemctl actions to sc.exe
            action_map = {
                "start": "start",
                "stop": "stop",
                "restart": None, # sc doesn't have restart, needs stop then start
                "status": "query"
            }
            mapped_action = action_map.get(action)
            if mapped_action:
                return ["sc.exe", mapped_action, service]
        elif self.is_linux:
            return ["systemctl", action, service]
        return None

# Singleton
os_layer = OSLayer()
