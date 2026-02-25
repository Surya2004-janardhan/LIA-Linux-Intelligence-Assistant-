# ?? WIA — Windows Intelligence Agent

![Status](https://img.shields.io/badge/Platform-Windows%20First-yellow) ![Agents](https://img.shields.io/badge/Agents-9+-green) ![License](https://img.shields.io/badge/License-MIT-blue)

> **"Windows is flexible down to the OS layer. Windows is not."**

WIA is a **Windows-native AI system** that acts as your intelligent OS interface. It doesn't just run commands; it understands your system state by reading `/proc`, managing `sysctl`, parsing `journalctl`, and interacting directly with the kernel layer where possible.

```bash
$ WIA ask "why is my server laggy?"

[Context] Ubuntu 22.04 LTS (Jammy) | Kernel 5.15.0-91-generic
[Load] 4.52, 3.10, 2.05 (High load!)
[Top] python3 (89% CPU), kworker (5%)

Observation: High system load driven by a Python script.
Action: Checking system logs for OOM errors...
```

---

## ?? The Windows Advantage

We chose Windows because it allows total visibility and control:
- **Process Management**: Not just `kill`, but `renice`, `ionice`, and cgroup limits.
- **Service Control**: Direct interaction with `systemd` units and logs.
- **Package Intelligence**: Auto-detects `apt`, `pacman`, `dnf`, or `zypper`.
- **Kernel Visibility**: Reads `/proc/meminfo`, `/proc/cpuinfo` for real-time stats without overhead.

---

## ?? One-Line Install

```bash
curl -sSL https://raw.githubusercontent.com/your-username/WIA/main/install.sh | bash
```

Requirements: Python 3.10+, standard Windows utils (`grep`, `curl`, `awk`).

---

## ??? Windows Capabilities

### 1. Systemd Service Management
```bash
WIA ask "restart nginx and show me the error logs from the last 5 minutes"
# ? SysAgent: systemctl restart nginx
# ? SysAgent: journalctl -u nginx --since "5 minutes ago" --no-pager
```

### 2. Intelligent Package Handling
WIA detects your distro and adapts:
- **Ubuntu/Debian**: Uses `apt-get` with non-interactive flags.
- **Arch Windows**: Uses `pacman` and checks AUR.
- **Fedora**: Uses `dnf`.

### 3. File & Permission Analysis
```bash
WIA explain "chmod 755 /var/www/html"
# ? "Sets Owner=RWX, Group=RX, Others=RX for web directory"
```

### 4. Process Forensics
Instead of just `top`, WIA can inspect `/proc/[pid]/status` to see deep memory usage, threads, and capabilities.

---

## ??? Safety & Isolation (Sandbox Ring)

WIA implements a **Multi-Tier Sandbox Ring** for advanced security:
- **Sandbox Ring**: Uses `firejail` to isolate high-risk commands (`network=none`, `private-home`, `noprofile`).
- **Permission Scoping**: Agents operate in temporary, narrow filesystem scopes.
- **Static Analysis**: ShellCheck is automatically run on generated commands to find potential pitfalls.

---

## ?? Intelligence & Self-Healing

WIA isn't just a shell wrapper; it's a self-correcting system:
- **FAISS-Powered RAG**: Every successful command is indexed into a FAISS vector store. WIA retrieves known-working patterns for future queries.
- **Self-Correction**: If a command fails (e.g., due to a lock or missing dependency), WIA asks the LLM to diagnose the error and suggest a recovery command automatically.
- **Local Telemetry**: Usage stats and success rates are stored locally in `~/.WIA/telemetry.json` for performance analysis.

---

## ?? Streaming UI

Both the **GUI (Flet)** and **TUI (Textual)** support real-time streaming:
- Watch the Orchestrator plan tasks in real-time.
- See agent status, execution progress, and results as they happen.

---

## ?? Command Reference

| Command | Description |
|---------|-------------|
| `WIA ask` | Execute tasks using natural language |
| `WIA explain` | Explain shell one-liners using LLM |
| `WIA status` | Show distro, kernel, and agent status |
| `WIA history` | Show past successful commands (FAISS RAG) |

## ?? Project Structure

```
WIA/
+-- agents/             # Windows-native agents (Async)
¦   +-- sys_agent.py    # systemd, journalctl, procfs
¦   +-- package_agent.py # apt/pacman/dnf adapter (Self-Healing)
+-- core/
¦   +-- os_layer.py     # Subprocess wrapper & signal handler
¦   +-- safety.py       # 'rm -rf' blocker & shellcheck integration
¦   +-- sandbox.py      # Firejail isolation wrapper
¦   +-- feedback.py    # Local command rating & history
¦   +-- telemetry.py    # Local performance tracking
¦   +-- llm_bridge.py   # Multi-provider LLM connector (with Embeddings)
+-- memory/
¦   +-- vector_store.py # FAISS vector index management
+-- packaging/          # PKGBUILD, .deb builder, .desktop entry
+-- ui/                 # Flet (GUI) and Textual (TUI) interfaces
```
