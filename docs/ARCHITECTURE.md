# LIA Architecture

## System Overview

LIA (Local Intelligence Agent) is a multi-agent automation system designed for local-first, privacy-respecting task execution. It uses a **Dynamic Agent Swarm** coordinated by an LLM-powered Orchestrator.

---

## Core Design Principles

### 1. Two-Tier Smart Routing (Token Optimization)
The single most important architectural decision in LIA:
- **Tier 1 (Fast Path)**: Keyword matching + regex argument extraction. Costs **0 tokens**. Handles ~70% of tasks instantly.
- **Tier 2 (LLM Path)**: LLM-based tool selection. Costs ~200 tokens. Only for ambiguous tasks.

**Why this matters**: A 3-step plan in the old architecture used 4 LLM calls (~2000 tokens). With smart routing, most steps hit Tier 1, reducing total cost to ~500 tokens for the same plan.

### 2. Local-First Execution
- All agents use OS-native tools: `os.listdir()`, `psutil`, `subprocess`, `socket`
- LLM is only used for planning and ambiguity resolution
- No data leaves the machine unless explicitly enabled in Connections

### 3. Layered Security
```
User Query → Orchestrator → Permission Check → Agent → Tool → OS
                                  ↓
                          PermissionManager
                          (whitelist/blacklist)
```

---

## Data Flow

```
User Input
    │
    ▼
Orchestrator.plan()          ← 1 LLM call (~300 tokens)
    │
    ▼
JSON Plan: [{agent, task}]
    │
    ▼ (for each step)
Agent.smart_execute(task)
    │
    ├─ Tier 1: Keyword match   ← 0 tokens (fast path)
    │      → extract_args()
    │      → tool.func(**args)
    │
    └─ Tier 2: LLM fallback    ← ~200 tokens (only if needed)
           → parse JSON
           → tool.func(**args)
    │
    ▼
Result → AuditManager.log()  → SQLite (audit_log.db)
    │
    ▼
Display (GUI / TUI / CLI)
```

---

## Directory Structure

```
LIA/
├── lia.py                  # Entry point (CLI, GUI, TUI)
├── config.yaml             # All settings (read + write)
├── requirements.txt        # Python dependencies
│
├── agents/                 # Specialist agents
│   ├── base_agent.py       # Abstract base with smart routing
│   ├── file_agent.py       # File operations (permission-aware)
│   ├── sys_agent.py        # System monitoring (psutil)
│   ├── git_agent.py        # Version control
│   ├── net_agent.py        # Network diagnostics (socket fallback)
│   ├── web_agent.py        # Browser automation
│   ├── connection_agent.py # 3rd-party integrations (opt-in)
│   ├── docker_agent.py     # Container management
│   ├── database_agent.py   # SQL operations (SELECT-only safety)
│   └── package_agent.py    # Package management (pip, npm, apt)
│
├── core/                   # Core infrastructure
│   ├── orchestrator.py     # LLM planner + agent coordinator
│   ├── llm_bridge.py       # LLM abstraction (Ollama/OpenAI)
│   ├── config.py           # Config read/write/save
│   ├── logger.py           # Structured logging
│   ├── audit.py            # Action audit trail (SQLite)
│   ├── memory_manager.py   # Central memory + system prompts
│   ├── permissions.py      # Path whitelisting/blacklisting
│   ├── guardian.py         # Background health monitor
│   ├── sandbox.py          # Firejail sandboxing (Linux)
│   └── workflow_engine.py  # YAML workflow executor
│
├── memory/                 # Persistent storage
│   ├── audit_log.db        # Action logs
│   ├── central_intelligence.db  # Knowledge base + system prompts
│   └── vector_index/       # FAISS embeddings
│
├── ui/                     # User interfaces
│   ├── gui.py              # Flet desktop GUI
│   └── tui.py              # Textual terminal UI
│
├── workflows/              # YAML automation routines
│   ├── friday_routine.yaml
│   ├── devops_morning.yaml
│   └── db_maintenance.yaml
│
└── docs/                   # Documentation
    ├── ARCHITECTURE.md     # This file
    ├── AGENTS.md           # Agent ecosystem guide
    ├── SECURITY.md         # Security model
    └── WORKFLOWS.md        # Workflow authoring guide
```

---

## Key Components

### Orchestrator
- Receives natural language, produces a JSON execution plan
- System prompt is **auto-generated** from registered agents (no hardcoding)
- Supports sequential and async (parallel) execution
- Per-step error isolation: one crash doesn't kill the whole plan

### LLM Bridge
- Abstracts Ollama, OpenAI, Anthropic via litellm
- Sync (`generate`) and async (`generate_async`) methods
- Single responsibility: no memory injection (kept separate)

### Central Memory
- SQLite with WAL mode for concurrent reads
- Connection pooling (single reused connection)
- Stores: knowledge base, system prompts, user preferences
- Frequency tracking learns what you use most

### Audit Manager
- Every agent action logged to SQLite
- Tracks: agent, task, result, status, tokens_used
- Result size capped at 2KB to prevent DB bloat
- Agent statistics aggregation for usage analysis

### Config
- YAML-based with dot-notation access (`config.get('llm.model')`)
- **Read AND Write**: `config.set('llm.model', 'mistral')` auto-saves
- GUI Settings tab uses this to persist changes

---

## Token Budget Analysis

| Operation | Old Cost | New Cost | Savings |
|-----------|----------|----------|---------|
| Orchestrator plan | ~800 tokens | ~300 tokens | 63% |
| Agent tool selection (obvious) | ~500 tokens | 0 tokens | 100% |
| Agent tool selection (ambiguous) | ~500 tokens | ~200 tokens | 60% |
| 3-step plan total | ~2300 tokens | ~300-900 tokens | 60-87% |

---

## Scalability

### Adding New Agents
1. Create `agents/new_agent.py` inheriting `LIAAgent`
2. Register tools with keywords for fast routing
3. Add to `lia.py` agents list
4. Orchestrator auto-discovers via `get_capabilities_prompt()`

### Performance at Scale
- SQLite WAL mode handles concurrent reads without locking
- Keyword routing is O(n) where n = number of keywords (typically <50)
- FAISS vector search is O(log n) for file lookup
- Guardian runs in a daemon thread, no main thread impact
