"""
WIA Explain Mode — Breaks down complex commands into readable explanations.

Usage: python WIA.py explain "find . -name '*.py' | xargs grep -l 'import os'"
"""
from core.llm_bridge import llm_bridge
from core.logger import logger


def explain_command(command: str) -> str:
    """
    Uses LLM to break down a command into human-readable parts.
    Works for shell commands, regex, awk, SQL, Docker, etc.
    """
    messages = [
        {
            "role": "system",
            "content": """You are a command explainer. Break down the given command into parts.
For each part, explain what it does in plain English.
Format:
COMMAND: <the full command>
───────────────────
<part> → <explanation>
<part> → <explanation>
...
SUMMARY: <one-line summary of what the whole command does>

Be concise. No markdown. No code blocks."""
        },
        {
            "role": "user",
            "content": f"Explain this command: {command}"
        }
    ]
    
    try:
        response = llm_bridge.generate(messages)
        if "Error connecting" in response:
            return _offline_explain(command)
        return response
    except Exception as e:
        logger.error(f"Explain mode failed: {e}")
        return _offline_explain(command)


def _offline_explain(command: str) -> str:
    """
    Fallback: Basic offline explanations for common commands.
    No LLM needed — uses pattern matching.
    """
    explanations = {
        "rm": "Remove/delete files or directories",
        "rm -rf": "Force-delete recursively without confirmation",
        "cp": "Copy files or directories",
        "mv": "Move or rename files",
        "chmod": "Change file permissions",
        "chown": "Change file ownership",
        "grep": "Search text with pattern matching",
        "find": "Search for files in directory tree",
        "awk": "Text processing and data extraction",
        "sed": "Stream editor for text transformation",
        "xargs": "Build and execute commands from stdin",
        "curl": "Transfer data from/to URL",
        "wget": "Download files from the web",
        "tar": "Archive files (tar.gz compression)",
        "ssh": "Secure shell remote connection",
        "scp": "Secure copy over SSH",
        "rsync": "Fast, versatile file sync",
        "docker": "Container management",
        "git": "Version control operations",
        "pip": "Python package manager",
        "npm": "Node.js package manager",
        "systemctl": "Linux service management",
        "journalctl": "View system logs",
        "ps": "List running processes",
        "kill": "Terminate a process",
        "df": "Show disk space usage",
        "du": "Show file/directory sizes",
        "top": "Real-time process monitor",
        "htop": "Interactive process viewer",
    }
    
    parts = command.split()
    if not parts:
        return "Empty command."
    
    lines = [f"COMMAND: {command}", "─" * 40]
    
    for i, part in enumerate(parts):
        # Check for pipe
        if part == "|":
            lines.append(f"  |  → Pipe: send output of left command as input to right command")
            continue
        if part == ">":
            lines.append(f"  >  → Redirect: write output to file (overwrite)")
            continue
        if part == ">>":
            lines.append(f"  >> → Redirect: append output to file")
            continue
        if part == "&&":
            lines.append(f"  && → Run next command only if previous succeeded")
            continue
        if part == "||":
            lines.append(f"  || → Run next command only if previous failed")
            continue
        
        # Check base command
        base = part.lstrip("./")
        if base in explanations:
            lines.append(f"  {part} → {explanations[base]}")
        elif part.startswith("-"):
            lines.append(f"  {part} → Flag/option")
        else:
            lines.append(f"  {part} → Argument")
    
    lines.append("─" * 40)
    lines.append("(Offline mode — run with Ollama for deeper analysis)")
    
    return "\n".join(lines)
