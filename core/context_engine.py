"""
WIA Context Engine — Dynamic system context injection.

Before the LLM generates any plan, this module gathers real-time system state
so the LLM can make informed decisions instead of hallucinating.

Example: "Why is my PC slow?" → injects CPU/RAM/disk state into the prompt
         "Move that file" → injects CWD file listing so LLM knows exact filenames
"""
import os
import psutil
import platform
from typing import Dict
from core.logger import logger
from core.os_layer import os_layer


class ContextEngine:
    """Gathers real-time system context and injects it into LLM prompts."""
    
    def __init__(self):
        self._cache = {}
        self._cache_ttl = {}
    
    def get_context(self, query: str) -> str:
        """
        Generates relevant context based on the query.
        Returns a compact context string to prepend to the LLM prompt.
        """
        context_parts = []
        
        # Always include: OS info (cheap, static)
        context_parts.append(self._os_context())
        
        # Always include: CWD contents (so LLM knows real filenames)
        context_parts.append(self._cwd_context())
        
        # Conditional: System resources (if query seems performance-related)
        if self._is_performance_query(query):
            context_parts.append(self._resource_context())
        
        # Conditional: Git state (if query seems git-related)
        if self._is_git_query(query):
            context_parts.append(self._git_context())
        
        # Conditional: Network state (if query seems network-related)
        if self._is_network_query(query):
            context_parts.append(self._network_context())
        
        # Conditional: Docker state
        if self._is_docker_query(query):
            context_parts.append(self._docker_context())
        
        return "\n".join([p for p in context_parts if p])
    
    # ─── CONTEXT GATHERERS ────────────────────────────────────────
    
    def _os_context(self) -> str:
        return (f"[OS] {platform.system()} {platform.release()} "
                f"({platform.machine()}) | Python {platform.python_version()}")
    
    def _cwd_context(self) -> str:
        """Lists current directory files so LLM can reference real names."""
        try:
            cwd = os.getcwd()
            items = os.listdir(cwd)
            
            # Separate dirs and files, cap at 30 items
            dirs = sorted([i for i in items if os.path.isdir(os.path.join(cwd, i))])[:15]
            files = sorted([i for i in items if os.path.isfile(os.path.join(cwd, i))])[:15]
            
            dir_str = ", ".join(dirs) if dirs else "none"
            file_str = ", ".join(files) if files else "none"
            
            return f"[CWD] {cwd}\n[Dirs] {dir_str}\n[Files] {file_str}"
        except Exception:
            return f"[CWD] {os.getcwd()}"
    
    def _resource_context(self) -> str:
        """CPU, RAM, disk usage for performance queries."""
        try:
            cpu = psutil.cpu_percent(interval=0.5)
            ram = psutil.virtual_memory()
            
            # Top 5 CPU-hungry processes
            procs = []
            for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent']):
                try:
                    procs.append(p.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            procs.sort(key=lambda x: x.get('cpu_percent', 0) or 0, reverse=True)
            top_procs = ", ".join([f"{p['name']}({p.get('cpu_percent',0):.0f}%)" for p in procs[:5]])
            
            return (f"[System] CPU: {cpu}% | RAM: {ram.percent}% "
                    f"({ram.available // (1024**2)}MB free)\n"
                    f"[Top Processes] {top_procs}")
        except Exception as e:
            return f"[System] Could not gather: {e}"
    
    def _git_context(self) -> str:
        """Current branch + status for git queries."""
        try:
            branch = os_layer.run_command(['git', 'branch', '--show-current'], timeout=5)
            status = os_layer.run_command(['git', 'status', '--short'], timeout=5)
            
            if not branch["success"]:
                return "[Git] Not a git repository"
            
            branch_name = branch["stdout"].strip()
            changes = status["stdout"].strip() if status["success"] else "unknown"
            change_count = len(changes.split('\n')) if changes else 0
            
            return f"[Git] Branch: {branch_name} | {change_count} changed files"
        except Exception:
            return ""
    
    def _network_context(self) -> str:
        """Basic connectivity state."""
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return "[Network] Internet: Connected"
        except OSError:
            return "[Network] Internet: Disconnected"
    
    def _docker_context(self) -> str:
        """Running containers."""
        result = os_layer.run_command(['docker', 'ps', '--format', '{{.Names}}: {{.Status}}'], timeout=5)
        if result["success"] and result["stdout"]:
            containers = result["stdout"].strip().split('\n')[:5]
            return f"[Docker] Running: {', '.join(containers)}"
        return "[Docker] No containers running (or Docker not installed)"
    
    # ─── QUERY CLASSIFIERS ────────────────────────────────────────
    
    def _is_performance_query(self, query: str) -> bool:
        keywords = ["slow", "lag", "freeze", "memory", "ram", "cpu", "disk", "space",
                     "performance", "speed", "hanging", "kill process", "top", "resource"]
        return any(kw in query.lower() for kw in keywords)
    
    def _is_git_query(self, query: str) -> bool:
        keywords = ["git", "commit", "push", "pull", "branch", "merge", "pr", "diff", "stash"]
        return any(kw in query.lower() for kw in keywords)
    
    def _is_network_query(self, query: str) -> bool:
        keywords = ["network", "internet", "ping", "dns", "connect", "wifi", "port", "curl"]
        return any(kw in query.lower() for kw in keywords)
    
    def _is_docker_query(self, query: str) -> bool:
        keywords = ["docker", "container", "compose", "image"]
        return any(kw in query.lower() for kw in keywords)


# Singleton
context_engine = ContextEngine()
