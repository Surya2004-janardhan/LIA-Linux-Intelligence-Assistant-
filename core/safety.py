"""
LIA Safety Guardrails — Destructive command detection, dry-run mode, and command validation.

This is the layer between the LLM output and actual execution.
Every command passes through here before touching the OS.
"""
import re
import shutil
import subprocess
from typing import Tuple, Optional
from core.logger import logger

# ─── HIGH-RISK COMMAND PATTERNS ──────────────────────────────────
# These require double confirmation or are outright blocked.

BLOCKED_COMMANDS = [
    # Filesystem destroyers
    r"rm\s+-rf\s+/\s*$",           # rm -rf /
    r"rm\s+-rf\s+/\*",             # rm -rf /*
    r"rm\s+-rf\s+~\s*$",           # rm -rf ~
    r"rm\s+-rf\s+\.\s*$",          # rm -rf .
    r"del\s+/s\s+/q\s+C:\\",       # Windows: del /s /q C:\
    r"format\s+[A-Z]:",            # format C:
    r"mkfs\.",                     # mkfs.ext4 etc
    r"dd\s+if=.*of=/dev/sd",      # dd to disk devices
    r">\s*/dev/sda",               # redirect to raw disk
    r"chmod\s+-R\s+777\s+/",      # chmod 777 everything
    r"chown\s+-R\s+.*\s+/\s*$",   # chown everything from root
]

HIGH_RISK_COMMANDS = [
    # Dangerous but sometimes legitimate
    r"rm\s+-rf",                   # Any rm -rf
    r"rm\s+-r",                    # Recursive delete
    r"rmdir\s+/s",                 # Windows recursive delete
    r"sudo\s+rm",                  # sudo delete
    r"kill\s+-9",                  # Force kill
    r"pkill",                      # Process kill
    r"shutdown",                   # System shutdown
    r"reboot",                     # System reboot
    r"systemctl\s+stop",           # Stop services
    r"iptables\s+-F",              # Flush firewall
    r"docker\s+system\s+prune",    # Docker cleanup
    r"git\s+push\s+--force",       # Force push
    r"git\s+reset\s+--hard",       # Hard reset
    r"DROP\s+TABLE",               # SQL drop
    r"DELETE\s+FROM",              # SQL delete
    r"TRUNCATE",                   # SQL truncate
    r"pip\s+uninstall",            # Package removal
    r"npm\s+uninstall\s+-g",       # Global package removal
]

# Commands that support dry-run flags
DRY_RUN_MAP = {
    "rsync": "--dry-run",
    "apt": "--simulate",
    "apt-get": "--simulate", 
    "dnf": "--assumeno",
    "pip": "--dry-run",
    "rm": None,  # No native dry-run, we intercept
    "git push": "--dry-run",
    "git clean": "--dry-run",
    "docker-compose up": "--no-start",
}


class SafetyGuard:
    """
    Validates commands before execution.
    Three levels: BLOCKED (never), HIGH_RISK (double confirm), SAFE (proceed).
    """
    
    def __init__(self):
        self.blocked_patterns = [re.compile(p, re.I) for p in BLOCKED_COMMANDS]
        self.high_risk_patterns = [re.compile(p, re.I) for p in HIGH_RISK_COMMANDS]
        self.shellcheck_path = shutil.which("shellcheck")
    
    def assess_risk(self, command: str) -> Tuple[str, str]:
        """
        Returns (risk_level, reason).
        risk_level: "BLOCKED", "HIGH_RISK", "SAFE"
        """
        # Check blocked first
        for pattern in self.blocked_patterns:
            if pattern.search(command):
                return "BLOCKED", f"Catastrophic command detected: matches '{pattern.pattern}'"
        
        # Check high risk
        for pattern in self.high_risk_patterns:
            if pattern.search(command):
                return "HIGH_RISK", f"Destructive command detected: matches '{pattern.pattern}'"
        
        return "SAFE", "Command appears safe"
    
    def get_dry_run_version(self, command: str) -> Optional[str]:
        """
        Returns a dry-run version of the command if supported.
        Returns None if dry-run not supported for this command.
        """
        for cmd_prefix, flag in DRY_RUN_MAP.items():
            if command.strip().startswith(cmd_prefix) and flag:
                # Insert dry-run flag after the command name
                parts = command.split()
                # Find where to insert
                for i, part in enumerate(parts):
                    if part == cmd_prefix.split()[-1]:
                        parts.insert(i + 1, flag)
                        return " ".join(parts)
        return None

    def run_static_analysis(self, command: str) -> Optional[str]:
        """
        Runs shellcheck on the command string if available.
        Returns a warning string if issues found, else None.
        """
        if not self.shellcheck_path:
            return None
        
        try:
            # We explicitly output to json to parse it, or plain text for easy display
            proc = subprocess.run(
                [self.shellcheck_path, "-"],
                input=f"#!/bin/sh\n{command}",
                text=True,
                capture_output=True
            )
            
            if proc.returncode != 0 and proc.stdout:
                # Filter out the sheath header
                warnings = [line for line in proc.stdout.splitlines() if "In -" not in line and line.strip()]
                if warnings:
                    return "\n".join(warnings)
            return None
        except Exception as e:
            logger.warning(f"Shellcheck failed: {e}")
            return None
    
    def validate_command(self, command: str) -> dict:
        """
        Full validation pipeline. Returns assessment with risk, dry-run option, and formatted output.
        """
        risk_level, reason = self.assess_risk(command)
        dry_run = self.get_dry_run_version(command)
        static_analysis = self.run_static_analysis(command)
        
        result = {
            "command": command,
            "risk_level": risk_level,
            "reason": reason,
            "dry_run_available": dry_run is not None,
            "dry_run_command": dry_run,
            "static_analysis": static_analysis,
            "allow_execution": risk_level != "BLOCKED",
            "suggest_sandbox": risk_level == "HIGH_RISK"
        }
        
        if risk_level == "BLOCKED":
            logger.warning(f"SAFETY BLOCK: {command} — {reason}")
        elif risk_level == "HIGH_RISK":
            logger.warning(f"HIGH RISK: {command} — {reason}")
        
        if static_analysis:
            logger.info(f"Static Analysis Warning for '{command}': {static_analysis}")
            
        return result
    
    def format_risk_display(self, assessment: dict) -> str:
        """Formats the risk assessment for CLI/GUI display."""
        risk = assessment["risk_level"]
        static_warn = assessment.get("static_analysis")
        
        sections = []
        
        if risk == "BLOCKED":
            sections.append(f"🚫 BLOCKED — This command is too dangerous to execute.\n"
                           f"   Reason: {assessment['reason']}\n"
                           f"   Command: {assessment['command']}")
        
        elif risk == "HIGH_RISK":
            sections.append(f"⚠️  HIGH RISK — This command may cause data loss.\n"
                           f"   Reason: {assessment['reason']}\n"
                           f"   Command: {assessment['command']}")
            if assessment["dry_run_available"]:
                sections.append(f"   💡 Dry-run available: {assessment['dry_run_command']}")
            sections.append(f"   Type 'yes' to confirm, 'dry' to dry-run, or 'no' to cancel.")
        
        else:
            sections.append(f"✅ SAFE: {assessment['command']}")

        if static_warn:
            sections.append(f"\n🔍 Static Analysis (ShellCheck):\n{static_warn}")

        return "\n".join(sections)


# Singleton
safety_guard = SafetyGuard()
