# 🐧 LIA — Linux Intelligence Agent

![Status](https://img.shields.io/badge/Platform-Linux%20First-yellow) ![Agents](https://img.shields.io/badge/Agents-9+-green) ![License](https://img.shields.io/badge/License-MIT-blue)

> **"Linux is flexible down to the OS layer. Windows is not."**

LIA is a **Linux-native AI system** that acts as your intelligent OS interface. It doesn't just run commands; it understands your system state by reading `/proc`, managing `sysctl`, parsing `journalctl`, and interacting directly with the kernel layer where possible.

```bash
$ lia ask "why is my server laggy?"

[Context] Ubuntu 22.04 LTS (Jammy) | Kernel 5.15.0-91-generic
[Load] 4.52, 3.10, 2.05 (High load!)
[Top] python3 (89% CPU), kworker (5%)

Observation: High system load driven by a Python script.
Action: Checking system logs for OOM errors...
```

---

## 🚀 The Linux Advantage

We chose Linux because it allows total visibility and control:
- **Process Management**: Not just `kill`, but `renice`, `ionice`, and cgroup limits.
- **Service Control**: Direct interaction with `systemd` units and logs.
- **Package Intelligence**: Auto-detects `apt`, `pacman`, `dnf`, or `zypper`.
- **Kernel Visibility**: Reads `/proc/meminfo`, `/proc/cpuinfo` for real-time stats without overhead.

---

## 📦 One-Line Install

```bash
curl -sSL https://raw.githubusercontent.com/your-username/LIA/main/install.sh | bash
```

Requirements: Python 3.10+, standard Linux utils (`grep`, `curl`, `awk`).

---

## 🛠️ Linux Capabilities

### 1. Systemd Service Management
```bash
lia ask "restart nginx and show me the error logs from the last 5 minutes"
# → SysAgent: systemctl restart nginx
# → SysAgent: journalctl -u nginx --since "5 minutes ago" --no-pager
```

### 2. Intelligent Package Handling
LIA detects your distro and adapts:
- **Ubuntu/Debian**: Uses `apt-get` with non-interactive flags.
- **Arch Linux**: Uses `pacman` and checks AUR.
- **Fedora**: Uses `dnf`.

### 3. File & Permission Analysis
```bash
lia explain "chmod 755 /var/www/html"
# → "Sets Owner=RWX, Group=RX, Others=RX for web directory"
```

### 4. Process Forensics
Instead of just `top`, LIA can inspect `/proc/[pid]/status` to see deep memory usage, threads, and capabilities.

---

## 🛡️ Safety Guard (Linux Edition)

Three security rings to prevent system damage:

1.  **User Ring (Safe)**: `ls`, `grep`, `cat`, `uptime` — Runs freely.
2.  **Admin Ring (Check)**: `systemctl`, `apt`, `docker` — Requires user confirmation.
3.  **Kernel Ring (Blocked)**: `rm -rf /`, `mkfs`, `dd`, `:(){ :|:& };:` (fork bombs) — **Hard blocked**.

---

## 🧠 System Architecture

```
USER TASK: "Clean up old docker images and update the system"
    │
    ▼
[CONTEXT ENGINE]
 Reads /etc/os-release → "Ubuntu 22.04"
 Checks /var/run/docker.sock → "Docker active"
    │
    ▼
[ORCHESTRATOR]
 Plan:
  1. DockerAgent: docker system prune -f
  2. PackageAgent: apt-get update && apt-get upgrade -y
    │
    ▼
[SAFETY GUARD]
 "docker prune" → HIGH RISK (Destructive)
 "apt-get upgrade" → SAFE (Standard maint)
    │
    ▼
[EXECUTION] (via OS Layer)
```

---

## 📋 Command Reference

| Command | Description |
|---------|-------------|
| `lia ask` | Execute tasks using natural language |
| `lia explain` | Explain shell one-liners using LLM |
| `lia status` | Show distro, kernel, and agent status |
| `lia index` | Index `/home` files for semantic search |
| `lia history` | Show past successful commands (RAG) |

## 📦 Project Structure

```
LIA/
├── agents/             # Linux-native agents
│   ├── sys_agent.py    # systemd, journalctl, procfs
│   ├── package_agent.py # apt/pacman/dnf adapter
│   └── ...
├── core/
│   ├── os_layer.py     # Subprocess wrapper & signal handler
│   ├── safety.py       # 'rm -rf' blocker & shellcheck integration
│   └── context.py      # /proc reader & distro detector
└── install.sh          # Bash installer
```
