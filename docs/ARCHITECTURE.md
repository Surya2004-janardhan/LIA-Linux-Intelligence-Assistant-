# WIA Architecture — Production System Design

## System Overview

WIA is a **local-first, multi-agent OS wrapper** that uses a local LLM to translate natural language into system actions. Every OS interaction passes through abstraction layers that enforce safety, permissions, and auditability.

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INTERFACES                             │
│  CLI (WIA.py) ──── GUI (Flet) ──── TUI (Textual/Rich)         │
└─────────────┬───────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR                                │
│  1. Context Engine → injects CWD, CPU, Git, Docker state       │
│  2. RAG Lookup → retrieves past successful commands             │
│  3. LLM Planning → generates multi-step plan                   │
│  4. Safety Guard → validates commands before execution          │
│  5. Feedback → records results for future RAG                   │
└─────────────┬───────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AGENT SWARM (9 specialists)                   │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐         │
│  │ FileAgent│ │ SysAgent │ │ GitAgent │ │ NetAgent │         │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘         │
│  ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐ ┌────┴─────┐         │
│  │ WebAgent │ │Connection│ │ Docker   │ │ Database │         │
│  └────┬─────┘ │  Agent   │ │  Agent   │ │  Agent   │         │
│       │       └──────────┘ └──────────┘ └────┬─────┘         │
│  ┌────┴─────┐                                │               │
│  │ Package  │     Each agent uses             │               │
│  │  Agent   │     Two-Tier Smart Routing      │               │
│  └──────────┘     (keyword → LLM fallback)    │               │
└─────────────┬─────────────────────────────────┘───────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   CORE ENGINE LAYER                             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐           │
│  │  OS Layer   │  │ Permission  │  │   Safety     │           │
│  │ (singleton) │  │  Manager    │  │   Guard      │           │
│  │ • signals   │  │ • paths     │  │ • blacklist  │           │
│  │ • subprocess│  │ • agents    │  │ • dry-run    │           │
│  │ • platform  │  │ • connections│  │ • risk tiers │           │
│  │ • cleanup   │  │ • cache     │  │              │           │
│  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘           │
│         │                │                │                    │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────┴───────┐           │
│  │  LLM Bridge │  │   Errors    │  │  Context     │           │
│  │ • Ollama    │  │ • 60+ codes │  │  Engine      │           │
│  │ • OpenAI    │  │ • severity  │  │ • CWD files  │           │
│  │ • Groq      │  │ • recovery  │  │ • CPU/RAM    │           │
│  │ • litellm   │  │   hints     │  │ • Git/Docker │           │
│  └─────────────┘  └─────────────┘  └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PERSISTENCE LAYER                             │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐           │
│  │  Audit DB   │  │  Memory DB  │  │  Feedback DB │           │
│  │ • actions   │  │ • knowledge │  │ • history    │           │
│  │ • tokens    │  │ • prompts   │  │ • ratings    │           │
│  │ • status    │  │ • facts     │  │ • RAG index  │           │
│  └─────────────┘  └─────────────┘  └──────────────┘           │
│  ┌─────────────┐  ┌─────────────┐                              │
│  │ FAISS Index │  │  Config     │                              │
│  │ • vectors   │  │ • YAML r/w  │                              │
│  │ • semantic  │  │ • hot reload│                              │
│  └─────────────┘  └─────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: "Why is my PC slow?"

```
1. USER  → WIA.py ask "why is my PC slow?"
2. CLI   → Orchestrator.run("why is my PC slow?")
3. CONTEXT ENGINE
   ├─ Detects performance keywords → gathers CPU, RAM, top processes
   ├─ Gathers CWD file listing (always)
   └─ Returns: "[System] CPU: 89% | RAM: 94% | Top: chrome(45%)"
4. FEEDBACK RAG
   ├─ Searches command_history for similar queries
   └─ Returns: "Past: 'check cpu' → SysAgent, check_cpu ⭐⭐⭐⭐⭐"
5. LLM PLANNING (1 call, ~300 tokens)
   ├─ System prompt includes: agents + context + RAG hints
   └─ Returns: {"steps": [{"agent": "SysAgent", "task": "system_health"}]}
6. AGENT EXECUTION
   ├─ SysAgent.smart_execute("system_health")
   ├─ Tier 1: keyword "health" matches → calls system_health() → 0 tokens
   └─ Returns: "CPU: 89%, RAM: 94%, Top: chrome(45%)"
7. SAFETY: No command to validate (pure Python tool)
8. FEEDBACK: Records result, prompts user for rating
9. AUDIT: Logs agent, task, result, tokens, status
```

**Total cost: 1 LLM call (~300 tokens) + 0 agent tokens = ~300 tokens**  
**Traditional approach: 3 LLM calls (~1500 tokens)**

---

## Two-Tier Smart Routing

The core innovation that reduces token cost by ~70%.

```python
# Every agent inherits from base_agent.py:

def smart_execute(self, task: str) -> str:
    # TIER 1: Keyword match (0 tokens, <1ms)
    tool_name, confidence = self.match_tool_by_keywords(task)
    if tool_name and confidence >= 0.8:
        args = self.extract_args_from_task(task, tool_name)
        return self.tools[tool_name]["func"](**args)  # Direct call

    # TIER 2: LLM fallback (200+ tokens, 1-3 seconds)
    return self._llm_execute(task)
```

### Why This Works
- Simple tasks have strong keyword signals: "check RAM" → keyword "ram" → `check_ram()`
- Complex tasks need LLM reasoning: "make sure my system can handle a Node.js deployment"
- ~70% of real-world queries hit Tier 1

---

## OS Layer Abstraction

Every system interaction goes through `core/os_layer.py`:

```python
# Instead of:
subprocess.run(["ping", "-c", "4", "google.com"])  # Breaks on Windows

# Agents use:
os_layer.run_command(os_layer.get_ping_cmd("google.com"), timeout=15)
# Returns: {"success": True, "stdout": "...", "duration_ms": 234, "timed_out": False}
```

**Benefits:**
- Platform-correct commands (Linux/Windows/Mac)
- Structured results instead of raw stdout
- Timeout protection on all subprocesses
- Process lifecycle management (cleanup on shutdown)
- Signal handling for graceful shutdown

---

## Safety Pipeline

Commands pass through `core/safety.py` before execution:

```
Command → SafetyGuard.validate_command()
  ├─ BLOCKED (rm -rf /, mkfs, dd to /dev) → Rejected, logged
  ├─ HIGH_RISK (rm -rf, sudo rm, git push --force) → Double confirm + dry-run offer
  └─ SAFE (ls, ping, git status) → Proceed
```

Dry-run support: `rsync → rsync --dry-run`, `apt → apt --simulate`, `pip → pip --dry-run`

---

## Permission Model

```
core/permissions.py (singleton)
  │
  ├─ Path Whitelist (configurable, resolves symlinks)
  │   ~/Documents, ~/Downloads, ~/Desktop, ./
  │
  ├─ Path Blacklist (hardcoded, never overridable)
  │   C:\Windows, /etc, /proc, /sys, /dev
  │
  ├─ Agent Operation Scoping
  │   FileAgent  → READ, WRITE, EXECUTE
  │   SysAgent   → READ, EXECUTE
  │   DatabaseAgent → READ only
  │
  └─ Connection Kill-Switches
      Gmail     → OFF by default
      Calendar  → OFF by default
      CustomAPI → OFF by default
```

---

## Error System

Every error is typed with a code, severity, and recovery suggestion:

```python
# Instead of: return "Error: file not found"
# Agents use:
return str(WIAResult.fail(
    ErrorCode.FILE_NOT_FOUND,       # Code 201
    "File not found: report.pdf",   # Message
    severity=ErrorSeverity.MEDIUM,  # Severity
    suggestion="Check the path"     # Auto-generated if not provided
))

# Output:
# [FILE_NOT_FOUND] File not found: report.pdf
#   💡 Fix: Check the file path and try again
```

Error domains: Permission (1xx), File (2xx), Network (3xx), LLM (4xx), Agent (5xx), System (6xx), Config (7xx)

---

## Feedback Loop (RAG)

```
1. User runs: WIA ask "check disk space"
2. SysAgent executes → "C: 85% used (50GB free)"
3. User rates: ⭐⭐⭐⭐⭐
4. Stored in: memory/feedback.db

Next time someone asks "how much disk space do I have?":
1. RAG finds: "check disk space" → SysAgent, check_disk, rating=5
2. Orchestrator adds this hint to LLM prompt
3. LLM knows exactly which agent/tool to use → faster, cheaper
```

---

## File Map

| File | Purpose | Lines |
|------|---------|-------|
| `WIA.py` | Entry point, CLI commands, rich output | ~190 |
| `core/orchestrator.py` | Plan + execute with context/RAG | ~130 |
| `core/os_layer.py` | OS abstraction, signals, subprocess | ~200 |
| `core/safety.py` | Destructive command guardrails | ~130 |
| `core/permissions.py` | Path/agent/connection access control | ~160 |
| `core/context_engine.py` | Dynamic system state injection | ~130 |
| `core/feedback.py` | Command history, ratings, RAG | ~170 |
| `core/errors.py` | Typed error codes + recovery hints | ~120 |
| `core/explain.py` | Command breakdown engine | ~100 |
| `core/llm_bridge.py` | LLM abstraction (Ollama/OpenAI) | ~60 |
| `core/audit.py` | Full audit trail with token tracking | ~55 |
| `core/memory_manager.py` | Central memory + system prompts | ~100 |
| `core/config.py` | Read/write YAML config | ~30 |
| `agents/base_agent.py` | Two-tier smart routing base class | ~100 |
| `agents/*.py` | 9 specialist agents | ~80 each |

---

## Adding a New Agent (5 minutes)

1. Create `agents/your_agent.py`, extend `WIAAgent`
2. Register tools with keywords in `__init__`
3. Implement `extract_args_from_task()` for regex extraction
4. Call `self.smart_execute(task)` in `execute()`
5. Import and add to the agents list in `WIA.py`

The Orchestrator auto-discovers it. No routing rules to update.

---

## Scalability Path

| Feature | Current | Next |
|---------|---------|------|
| Agents | 9 (sync) | Plugin system, lazy loading |
| LLM | Ollama local | Streaming, multi-provider routing |
| RAG | SQLite keyword search | FAISS vector similarity |
| Execution | Sequential + basic async | True async with dependency graphs |
| Packaging | pip install | .deb, .rpm, PKGBUILD, Homebrew |
