"""
WIA Safety Guardrails — Destructive command detection, dry-run mode, and command validation.

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
    # Filesystem destroyers (Windows)
    r"del\s+/s\s+/q\s+C:\\",       # del /s /q C:\
    r"rd\s+/s\s+/q\s+C:\\",        # rd /s /q C:\
    r"format\s+[A-Z]:",            # format C:
    r"Remove-Item\s+.*-Recurse\s+.*C:\\", # PowerShell delete root
    r"reg\s+delete\s+HKLM\\SYSTEM", # Registry destroyer
    r"rmdir\s+/s\s+/q\s+C:\\",     # rmdir /s /q C:\
    
    # Cross-platform / Generic
    r"dd\s+if=.*of=\\\\.\PhysicalDrive", # dd to physical drive
    r"mkfs\.",                     # Just in case WSL or similar
]

HIGH_RISK_COMMANDS = [
    # Dangerous but sometimes legitimate (Windows)
    r"del\s+/s\s+/q",              # Recursive delete
    r"rmdir\s+/s\s+/q",            # Recursive rmdir
    r"net\s+stop",                 # Stop system services
    r"sc\s+stop",                  # Stop services via sc
    r"Stop-Service",               # PowerShell stop service
    r"shutdown\s+/s",              # System shutdown
    r"reboot\s+/r",                # System reboot
    r"Remove-Item\s+.*-Recurse",   # PowerShell recursive delete
    r"taskkill\s+/f",              # Force kill
    
    # Generic destructive
    r"docker\s+system\s+prune",    # Docker cleanup
    r"git\s+push\s+--force",       # Force push
    r"git\s+reset\s+--hard",       # Hard reset
    r"DROP\s+TABLE",               # SQL drop
    r"DELETE\s+FROM",              # SQL delete
    r"pip\s+uninstall",            # Package removal
    r"npm\s+uninstall\s+-g",       # Global package removal
]

# Commands that support dry-run flags (Windows equivalents)
DRY_RUN_MAP = {
    "rsync": "--dry-run",
    "pip": "--dry-run",
    "git push": "--dry-run",
    "git clean": "--dry-run",
    "powershell": "-WhatIf",
    "Remove-Item": "-WhatIf",
    "Copy-Item": "-WhatIf",
    "Move-Item": "-WhatIf",
}


class SafetyGuard:
    """
    Validates commands before execution.
    Three levels: BLOCKED (never), HIGH_RISK (double confirm), SAFE (proceed).
    """
    
    def __init__(self):
        self.blocked_patterns = [re.compile(p, re.I) for p in BLOCKED_COMMANDS]
        self.high_risk_patterns = [re.compile(p, re.I) for p in HIGH_RISK_COMMANDS]
        # PSScriptAnalyzer is the PowerShell equivalent of shellcheck
        self.psanalyzer_path = shutil.which("Invoke-ScriptAnalyzer")
    
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
        """
        # PowerShell -WhatIf support
        if "-WhatIf" not in command:
            for cmd_prefix in ["Remove-Item", "Copy-Item", "Move-Item", "Stop-Service"]:
                if cmd_prefix in command:
                    return f"{command} -WhatIf"

        for cmd_prefix, flag in DRY_RUN_MAP.items():
            if command.strip().startswith(cmd_prefix) and flag:
                if flag not in command:
                    return f"{command} {flag}"
        return None

    def run_static_analysis(self, command: str) -> Optional[str]:
        """
        Runs a basic syntax check for PowerShell commands.
        """
        if "powershell" not in command.lower() and not self.psanalyzer_path:
            return None
        
        # We can implement a basic PowerShell syntax check if needed
        # For now, we'll just log that we would run analysis
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
            "suggest_sandbox": False # Sandboxing disabled for now on Windows
        }
        
        if risk_level == "BLOCKED":
            logger.warning(f"SAFETY BLOCK: {command} — {reason}")
        elif risk_level == "HIGH_RISK":
            logger.warning(f"HIGH RISK: {command} — {reason}")
            
        return result
    
    def format_risk_display(self, assessment: dict) -> str:
        """Formats the risk assessment for CLI/GUI display."""
        risk = assessment["risk_level"]
        
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
                sections.append(f"   💡 Dry-run available (-WhatIf): {assessment['dry_run_command']}")
            sections.append(f"   Type 'yes' to confirm, 'dry' to dry-run, or 'no' to cancel.")
        
        else:
            sections.append(f"✅ SAFE: {assessment['command']}")

        return "\n".join(sections)


# Singleton
safety_guard = SafetyGuard()


# Singleton
safety_guard = SafetyGuard()
