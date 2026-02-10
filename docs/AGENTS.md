# LIA Agent System Documentation

## Overview
LIA employs a **6-Agent Specialist Swarm** architecture. Each agent is a domain expert with its own tools and capabilities.

---

## 1. FileAgent
**Domain**: Filesystem operations  
**Capabilities**:
- List directory contents
- Move/copy files
- Create directories
- Find files by pattern
- **Permission-Aware**: Only accesses whitelisted folders

**Example Tasks**:
- "organize my Downloads folder by file type"
- "find all PDFs in Documents"
- "create a backup folder"

---

## 2. SysAgent
**Domain**: System monitoring and service management  
**Capabilities**:
- CPU/RAM/Disk usage monitoring
- Service control (systemctl on Linux)
- Process management
- Health checks

**Example Tasks**:
- "check my RAM usage"
- "restart nginx service"
- "show disk space"

---

## 3. GitAgent
**Domain**: Version control and code management  
**Capabilities**:
- Git status and commits
- GitHub CLI integration (gh)
- PR listing and management

**Example Tasks**:
- "commit all changes with message 'update docs'"
- "show me open pull requests"
- "what's the git status?"

---

## 4. NetAgent
**Domain**: Network diagnostics  
**Capabilities**:
- Ping hosts
- Port scanning (nmap)
- Network connectivity checks

**Example Tasks**:
- "ping google.com"
- "scan localhost for open ports"
- "check if I'm connected to the internet"

---

## 5. WebAgent
**Domain**: Browser automation and web navigation  
**Capabilities**:
- Open URLs
- Google search
- Deep linking to applications

**Example Tasks**:
- "search google for python tutorials"
- "open github.com"
- "launch my email client"

---

## 6. ConnectionAgent
**Domain**: Third-party integrations  
**Capabilities**:
- Gmail access (when enabled)
- Calendar management (when enabled)
- Custom API bridges

**Security**: All connections are **disabled by default** and require explicit user permission in `config.yaml`.

**Example Tasks**:
- "check my recent emails"
- "create a draft email to john@example.com"

---

## Agent Coordination

The **Orchestrator** acts as the central brain:
1. Receives natural language query
2. Consults **Central Memory** for system instructions
3. Generates a multi-step JSON plan
4. Routes tasks to appropriate agents
5. Can execute **sequentially** or **in parallel** (async mode)

### Parallel Execution
For complex workflows, LIA can run multiple agents concurrently:
```python
# Sequential (default)
results = orchestrator.run("check RAM and ping google")

# Parallel (async)
results = await orchestrator.run_async("check RAM and ping google")
```

---

## Central Memory System

LIA maintains a **tiered memory architecture**:

### Tier 1: Metadata Search (SQLite)
Fast lookups for file paths, user preferences, and agent history.

### Tier 2: Semantic Memory (FAISS)
Vector embeddings for context-aware file search.

### Tier 3: System Prompts
Global instructions that guide all agent behavior. Similar to Cursor/Claude's system-level directives.

**Location**: `memory/central_intelligence.db`

**Key Features**:
- Cross-session persistence
- Frequency tracking (learns what you use most)
- Category-based organization
