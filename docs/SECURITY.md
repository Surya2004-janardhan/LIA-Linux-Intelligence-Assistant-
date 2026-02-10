# Security & Permissions in LIA

LIA is built with a "Trust but Verify" philosophy. Since it executes real commands on your system, security is the top priority.

## 1. Audit Logging
Every action LIA takes is permanent and transparent.
- **Path**: `memory/audit_log.db` (SQLite).
- **Recorded Data**: Timestamp, Agent Name, Task, Execution Result, and Status.
- **Why**: Allows you to audit exactly what LIA did if something goes wrong.

## 2. Sandboxing (Firejail)
On Linux systems, LIA supports `Firejail` for isolation.
- **What it does**: Wraps CLI commands in a restricted profile.
- **Default Info**: Sandboxing is **disabled** by default in `config.yaml`.
- **Enabling**: Set `security.sandbox_enabled: true` in your config.

## 3. Privilege Escalation (Sudo)
LIA does **not** store your sudo password.
- **How it works**: If an agent executes a command that requires elevation (like `systemctl restart`), LIA triggers a native Linux/Windows prompt or the shell's built-in sudo mechanism.
- **User Choice**: You should always review the command in the LIA GUI before confirming execution of a plan.

## 4. Local-First Isolation
- LIA does not phone home.
- The LLM connection is strictly local (via Ollama) by default.
- If you use an external API (like OpenAI), your query *will* leave your machine, but LIA's internal memory (file paths, etc.) stays local.
