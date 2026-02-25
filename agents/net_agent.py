import socket
import re
from agents.base_agent import WIAAgent
from core.logger import logger
from core.os_layer import os_layer
from core.errors import WIAResult, ErrorCode

class NetAgent(WIAAgent):
    def __init__(self):
        super().__init__("NetAgent", ["Network diagnostics", "Ping", "Port scanning", "Connectivity"])
        
        self.register_tool("ping_host", self.ping_host, "Pings a host",
            keywords=["ping"])
        self.register_tool("check_ports", self.check_ports, "Scans ports on a target",
            keywords=["port", "scan", "nmap"])
        self.register_tool("check_connectivity", self.check_connectivity, "Quick internet check",
            keywords=["internet", "online", "connected", "connectivity"])
        self.register_tool("dns_lookup", self.dns_lookup, "Resolves a hostname to IP",
            keywords=["dns", "resolve", "lookup", "ip of"])

    def ping_host(self, host: str = "google.com") -> str:
        cmd = os_layer.get_ping_cmd(host, count=4)
        result = os_layer.run_command(cmd, timeout=15)
        if result["timed_out"]:
            return str(WIAResult.fail(ErrorCode.TIMEOUT, f"Ping to {host} timed out"))
        if not result["success"]:
            return str(WIAResult.fail(ErrorCode.HOST_UNREACHABLE, f"Cannot reach {host}: {result['stderr']}"))
        return f"✅ Ping {host}:\n{result['stdout']}\n({result['duration_ms']}ms total)"

    def check_ports(self, target: str = "localhost") -> str:
        # Try nmap first
        result = os_layer.run_command(['nmap', '-F', target], timeout=30)
        if result["success"]:
            return result["stdout"]
        
        # Fallback: Python socket scan (no dependency needed)
        return self._python_port_scan(target)

    def _python_port_scan(self, target: str) -> str:
        common_ports = {
            22: "SSH", 80: "HTTP", 443: "HTTPS", 3000: "Dev", 
            3306: "MySQL", 5432: "PostgreSQL", 5000: "Flask",
            8000: "Django", 8080: "Proxy", 8443: "Alt-HTTPS", 
            27017: "MongoDB", 6379: "Redis", 9200: "Elasticsearch"
        }
        open_ports = []
        for port, service in common_ports.items():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                if sock.connect_ex((target, port)) == 0:
                    open_ports.append(f"  {port:<6} {service}")
                sock.close()
            except Exception:
                pass
        
        if open_ports:
            header = f"Open ports on {target}:\n  {'Port':<6} Service\n  {'─' * 20}"
            return f"{header}\n" + "\n".join(open_ports)
        return f"No common ports open on {target}"

    def check_connectivity(self) -> str:
        """Instant internet check via socket — no subprocess, no LLM."""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return "Internet: Connected ✅"
        except OSError:
            return str(WIAResult.fail(ErrorCode.HOST_UNREACHABLE, "Internet: Disconnected ❌",
                suggestion="Check your network connection or firewall"))

    def dns_lookup(self, hostname: str = "google.com") -> str:
        try:
            ip = socket.gethostbyname(hostname)
            return f"{hostname} → {ip}"
        except socket.gaierror:
            return str(WIAResult.fail(ErrorCode.DNS_FAILURE, f"Cannot resolve: {hostname}"))

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        if tool_name == "ping_host":
            match = re.search(r'ping\s+(\S+)', task, re.I)
            return {"host": match.group(1) if match else "google.com"}
        if tool_name == "check_ports":
            match = re.search(r'(?:scan|ports?\s+(?:on|for)?)\s+(\S+)', task, re.I)
            return {"target": match.group(1) if match else "localhost"}
        if tool_name == "dns_lookup":
            match = re.search(r'(?:dns|resolve|lookup|ip\s+of)\s+(\S+)', task, re.I)
            return {"hostname": match.group(1) if match else "google.com"}
        return {}

    def execute(self, task: str) -> str:
        logger.info(f"NetAgent executing: {task}")
        return self.smart_execute(task)
