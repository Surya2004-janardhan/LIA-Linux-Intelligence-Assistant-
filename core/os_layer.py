"""
LIA OS Layer — The foundation that makes LIA a true OS wrapper.

This module provides:
1. Platform detection and capability mapping
2. Signal handling for graceful shutdown
3. Process lifecycle management
4. Environment isolation
5. Resource limits
6. INTEGRATED SAFETY GUARD (New)
"""
import os
import sys
import signal
import platform
import ctypes
import subprocess
import threading
from typing import Optional, Callable, List, Union
from core.logger import logger

# Lazy import to avoid circular dependency (safety -> os_layer)
# We import it inside the method or use a property
_safety_guard = None

def get_safety_guard():
    global _safety_guard
    if _safety_guard is None:
        from core.safety import safety_guard
        _safety_guard = safety_guard
    return _safety_guard


class OSLayer:
    """
    Singleton that wraps all OS interactions.
    Every agent MUST go through this layer — no direct os/subprocess calls.
    """
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
        
        # Platform info (detected once, reused everywhere)
        self.platform = platform.system().lower()  # 'windows', 'linux', 'darwin'
        self.is_windows = self.platform == "windows"
        self.is_linux = self.platform == "linux"
        self.is_mac = self.platform == "darwin"
        self.arch = platform.machine()
        self.hostname = platform.node()
        self.python_version = platform.python_version()
        
        # Track managed subprocesses for cleanup
        self._active_processes = []
        self._shutdown_hooks = []
        self._is_shutting_down = False
        
        # Register signal handlers for graceful shutdown
        self._register_signals()
        
        logger.info(f"OS Layer initialized: {self.platform}/{self.arch} on {self.hostname}")

    def _register_signals(self):
        """Register handlers for graceful shutdown."""
        try:
            signal.signal(signal.SIGINT, self._handle_shutdown)
            signal.signal(signal.SIGTERM, self._handle_shutdown)
        except (OSError, ValueError):
            # Signal handling not available (e.g., running in a thread)
            pass

    def _handle_shutdown(self, signum, frame):
        """Graceful shutdown: kill child processes, flush DBs, close connections."""
        if self._is_shutting_down:
            return
        self._is_shutting_down = True
        logger.info(f"Shutdown signal received ({signum}). Cleaning up...")
        
        # Kill managed subprocesses
        for proc in self._active_processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        
        # Run shutdown hooks (DB close, file flush, etc.)
        for hook in self._shutdown_hooks:
            try:
                hook()
            except Exception as e:
                logger.error(f"Shutdown hook failed: {e}")
        
        logger.info("Shutdown complete.")
        sys.exit(0)

    def register_shutdown_hook(self, hook: Callable):
        """Register a function to run on graceful shutdown."""
        self._shutdown_hooks.append(hook)

    # ─── SAFE SUBPROCESS EXECUTION ────────────────────────────────

    def run_command(self, cmd: Union[List[str], str], timeout: int = 30, cwd: str = None, 
                    env: dict = None, shell: bool = False) -> dict:
        """
        The ONLY way agents should run shell commands.
        Enforces Safety Guardrails before execution.
        """
        import time
        start = time.monotonic()
        
        # Normalize cmd to list if string
        if isinstance(cmd, str):
            cmd_str = cmd
            cmd_list = cmd.split()
        else:
            cmd_str = " ".join(cmd)
            cmd_list = cmd
            
        # 1. SAFETY CHECK
        guard = get_safety_guard()
        assessment = guard.validate_command(cmd_str)
        
        if assessment["risk_level"] == "BLOCKED":
            return {
                "success": False,
                "stdout": "",
                "stderr": f"SAFETY BLOCK: Command '{cmd_str}' is denied by policy.",
                "returncode": -1,
                "duration_ms": 0,
                "timed_out": False
            }
        
        if assessment["risk_level"] == "HIGH_RISK":
            # For now, we just log warning and proceed (or fail if strict mode)
            # In a real CLI, we'd ask for confirmation interactively, but agents run headless.
            # We fail high-risk commands in headless mode unless a 'force' flag is implemented.
            # config.get('security.block_destructive_commands') could be used here.
            # For this implementation, we'll return a specific error asking user to run manual.
            return {
                "success": False,
                "stdout": "",
                "stderr": f"HIGH RISK BLOCKED: '{cmd_str}' requires manual confirmation.\nReason: {assessment['reason']}",
                "returncode": -1,
                "duration_ms": 0,
                "timed_out": False
            }

        try:
            # Merge environment
            run_env = os.environ.copy()
            if env:
                run_env.update(env)
            
            # Use shell=True if explicitly requested OR platform requires it for certain tasks
            # But default to False for safety
            
            proc = subprocess.Popen(
                cmd_list if not shell else cmd_str,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
                env=run_env,
                shell=shell,
                # Prevent child from inheriting parent signals (Windows only)
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if self.is_windows else 0
            )
            self._active_processes.append(proc)
            
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                return {
                    "success": False,
                    "stdout": stdout,
                    "stderr": f"TIMEOUT: Command exceeded {timeout}s limit",
                    "returncode": -1,
                    "duration_ms": int((time.monotonic() - start) * 1000),
                    "timed_out": True
                }
            finally:
                if proc in self._active_processes:
                    self._active_processes.remove(proc)
            
            duration = int((time.monotonic() - start) * 1000)
            
            return {
                "success": proc.returncode == 0,
                "stdout": stdout.strip(),
                "stderr": stderr.strip(),
                "returncode": proc.returncode,
                "duration_ms": duration,
                "timed_out": False
            }
            
        except FileNotFoundError:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command not found: '{cmd_list[0]}'. Is it installed and in PATH?",
                "returncode": -1,
                "duration_ms": 0,
                "timed_out": False
            }
        except PermissionError:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Permission denied: Cannot execute '{cmd_list[0]}'",
                "returncode": -1,
                "duration_ms": 0,
                "timed_out": False
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Unexpected error: {str(e)}",
                "returncode": -1,
                "duration_ms": int((time.monotonic() - start) * 1000),
                "timed_out": False
            }

    # ─── SAFE FILE OPERATIONS ─────────────────────────────────────

    def path_exists(self, path: str) -> bool:
        try:
            return os.path.exists(path)
        except (OSError, ValueError):
            return False

    def is_dir(self, path: str) -> bool:
        try:
            return os.path.isdir(path)
        except (OSError, ValueError):
            return False

    def resolve_path(self, path: str) -> str:
        """Resolves to absolute path, handling ~, .., and symlinks."""
        try:
            expanded = os.path.expanduser(path)
            resolved = os.path.realpath(os.path.abspath(expanded))
            return resolved
        except Exception:
            return os.path.abspath(path)

    def safe_listdir(self, path: str) -> dict:
        """Lists directory with structured error handling."""
        resolved = self.resolve_path(path)
        try:
            if not os.path.exists(resolved):
                return {"success": False, "error": f"Path does not exist: {resolved}", "items": []}
            if not os.path.isdir(resolved):
                return {"success": False, "error": f"Not a directory: {resolved}", "items": []}
            items = os.listdir(resolved)
            return {"success": True, "items": items, "count": len(items), "path": resolved}
        except PermissionError:
            return {"success": False, "error": f"OS permission denied: {resolved}", "items": []}
        except Exception as e:
            return {"success": False, "error": str(e), "items": []}

    # ─── PLATFORM-AWARE COMMANDS ──────────────────────────────────

    def get_ping_cmd(self, host: str, count: int = 4) -> list:
        """Returns platform-correct ping command."""
        if self.is_windows:
            return ["ping", "-n", str(count), host]
        return ["ping", "-c", str(count), host]

    def get_service_cmd(self, service: str, action: str) -> Optional[list]:
        """Returns platform-correct service management command, or None if unsupported."""
        if self.is_linux:
            return ["systemctl", action, service]
        if self.is_mac:
            return ["brew", "services", action, service]
        return None  # Windows service management requires different approach

    def get_package_manager(self) -> str:
        """Detects the system package manager."""
        if self.is_windows:
            return "winget"
        if self.is_mac:
            return "brew"
        # Linux: detect distro
        for pm in ["apt", "dnf", "yum", "pacman", "zypper"]:
            result = self.run_command(["which", pm], timeout=5)
            if result["success"]:
                return pm
        return "unknown"

    # ─── SYSTEM INFO ──────────────────────────────────────────────

    def get_system_summary(self) -> dict:
        """Returns a comprehensive system info dict."""
        import psutil
        return {
            "platform": self.platform,
            "arch": self.arch,
            "hostname": self.hostname,
            "python": self.python_version,
            "cpu_count": psutil.cpu_count(),
            "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
            "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3) if not self.is_windows 
                                  else psutil.disk_usage('C:\\').free / (1024**3), 1),
        }


# Singleton
os_layer = OSLayer()
