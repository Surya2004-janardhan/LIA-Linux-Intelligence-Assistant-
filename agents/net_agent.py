import subprocess
import os
import socket
from agents.base_agent import LIAAgent
from core.logger import logger

class NetAgent(LIAAgent):
    def __init__(self):
        super().__init__("NetAgent", ["Network diagnostics", "Ping", "Port scanning", "Connectivity"])
        
        self.register_tool("ping_host", self.ping_host, "Pings a host to check connectivity",
            keywords=["ping"])
        self.register_tool("check_ports", self.check_ports, "Scans ports on a target",
            keywords=["port", "scan", "nmap"])
        self.register_tool("check_connectivity", self.check_connectivity, "Quick internet check",
            keywords=["internet", "online", "connected", "connectivity"])

    def ping_host(self, host: str = "google.com"):
        param = '-n' if os.name == 'nt' else '-c'
        try:
            result = subprocess.run(['ping', param, '4', host], capture_output=True, text=True, timeout=15)
            return result.stdout if result.returncode == 0 else f"Ping failed: {result.stderr}"
        except subprocess.TimeoutExpired:
            return f"Ping to {host} timed out."
        except Exception as e:
            return f"Error: {str(e)}"

    def check_ports(self, target: str = "localhost"):
        try:
            result = subprocess.run(['nmap', target], capture_output=True, text=True, timeout=30)
            return result.stdout if result.returncode == 0 else f"Nmap failed (is it installed?): {result.stderr}"
        except FileNotFoundError:
            # Fallback: use Python sockets for common ports (no nmap needed)
            return self._python_port_scan(target)
        except Exception as e:
            return f"Error: {str(e)}"

    def _python_port_scan(self, target: str):
        """OS-layer fallback: scan common ports using Python sockets instead of nmap."""
        common_ports = [22, 80, 443, 3000, 3306, 5432, 5000, 8000, 8080, 8443, 27017]
        open_ports = []
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex((target, port))
                if result == 0:
                    open_ports.append(port)
                sock.close()
            except:
                pass
        if open_ports:
            return f"Open ports on {target}: {', '.join(map(str, open_ports))}"
        return f"No common ports open on {target}"

    def check_connectivity(self):
        """Quick internet check using OS-level socket — no subprocess needed."""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return "Internet: Connected ✅"
        except OSError:
            return "Internet: Disconnected ❌"

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        import re
        if tool_name == "ping_host":
            match = re.search(r'ping\s+(\S+)', task, re.I)
            return {"host": match.group(1) if match else "google.com"}
        if tool_name == "check_ports":
            match = re.search(r'(?:scan|ports?\s+(?:on|for)?)\s+(\S+)', task, re.I)
            return {"target": match.group(1) if match else "localhost"}
        return {}

    def execute(self, task: str) -> str:
        logger.info(f"NetAgent executing task: {task}")
        return self.smart_execute(task)
