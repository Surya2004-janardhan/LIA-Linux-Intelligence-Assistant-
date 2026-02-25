# WIA (Windows Intelligence Assistant) 

**WIA** is a powerful, agentic AI assistant designed specifically for **Windows**. It bridges the gap between Large Language Models (LLMs) and the Windows ecosystem, allowing you to manage your system, files, networks, and development workflows through natural language.

---

##  Key Features

- **Agentic Core**: Multi-tier reasoning system with Keyword matching (Tier 1) and LLM fallback (Tier 2).
- **Windows Specialization**: Deep integration with PowerShell, sc.exe, winget, and Get-WinEvent.
- **Safety First**: Recursive dangerous command detection, -WhatIf (dry-run) support, and permission scoping.
- **Self-Correction**: AI-powered recovery from command failures or typos.
- **RAG Memory**: Local similarity search for past commands to improve speed and accuracy.

---

##  Components & Agents

- **SysAgent**: Monitor CPU/RAM, manage Windows Services, and audit Event Logs.
- **PackageAgent**: Install and update packages via winget, Chocolatey, pip, or 
pm.
- **GitAgent**: Manage repositories, commits, and branch workflows.
- **FileAgent**: Smart file search, content analysis, and management.
- **NetAgent**: Diagnostics, Port Scanning, and connectivity checks.
- **DockerAgent**: Control containers and images via Docker Desktop.

---

##  Installation (Windows)

1. **Prerequisites**: 
   - Python 3.10+
   - Ollama (recommended) or OpenAI API key.
2. **Setup**:
   `powershell
   # Open PowerShell and run the installer
   .\install.ps1
   `
3. **Configure**: Edit config/config.yaml to set your LLM provider and API keys.

---

##  Usage

`powershell
# Ask a question or give a task
python wia.py ask "Restart the Print Spooler service"
python wia.py ask "Check for system updates via winget"

# Explain a complex command
python wia.py explain "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10"

# Show system health
python wia.py status
`

---

##  Security & Safety

WIA includes a **Safety Guard** that:
- Blocks catastrophic commands (e.g., del /s /q C:\).
- Warns about high-risk actions.
- Automatically suggests -WhatIf (dry-run) for destructive PowerShell commands.

---

##  License

MIT License. See LICENSE for details.
