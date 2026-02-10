# LIA Agent Ecosystem

LIA employs a **Dynamic Multi-Agent Swarm** architecture. Each agent is a domain specialist with its own tools and capabilities. The system is designed to be **extensible**—new agents can be added without modifying core logic.

---

## Core Agents

### 1. FileAgent
**Domain**: Filesystem operations  
**Tools**: list_directory, move_file, create_directory, find_files  
**Security**: Permission-aware (only accesses whitelisted folders)

**Example Tasks**:
- "organize my Downloads by file type"
- "find all PDFs in Documents"
- "create a backup folder"

---

### 2. SysAgent
**Domain**: System monitoring and service management  
**Tools**: CPU/RAM/Disk monitoring, systemctl (Linux), process management

**Example Tasks**:
- "check my RAM usage"
- "restart nginx service"
- "show disk space"

---

### 3. GitAgent
**Domain**: Version control and code management  
**Tools**: git status, git commit, GitHub CLI (gh) integration

**Example Tasks**:
- "commit all changes with message 'update docs'"
- "show me open pull requests"
- "what's the git status?"

---

### 4. NetAgent
**Domain**: Network diagnostics  
**Tools**: ping, nmap port scanning, connectivity checks

**Example Tasks**:
- "ping google.com"
- "scan localhost for open ports"
- "check if I'm connected to the internet"

---

### 5. WebAgent
**Domain**: Browser automation and web navigation  
**Tools**: open URLs, Google search, deep linking

**Example Tasks**:
- "search google for python tutorials"
- "open github.com"
- "launch my email client"

---

## Integration Agents

### 6. ConnectionAgent
**Domain**: Third-party API integrations  
**Tools**: Gmail, Calendar, Custom APIs  
**Security**: All connections disabled by default, require explicit permission

**Example Tasks**:
- "check my recent emails"
- "create a draft email to john@example.com"

---

### 7. DockerAgent
**Domain**: Container orchestration  
**Tools**: docker ps, docker start/stop, docker-compose up

**Example Tasks**:
- "list all running containers"
- "start my postgres container"
- "run docker-compose in the current directory"

---

### 8. DatabaseAgent
**Domain**: Database operations  
**Tools**: SQLite queries, database backups, schema inspection

**Example Tasks**:
- "query the users table in myapp.db"
- "backup my database to /backups"
- "show me all tables in the database"

---

### 9. PackageAgent
**Domain**: Software package management  
**Tools**: pip, npm, apt, yum

**Example Tasks**:
- "install the requests library"
- "update system packages"
- "install express via npm"

---

## Agent Coordination

### The Orchestrator
The **Orchestrator** acts as the central intelligence:
1. Receives natural language query
2. Consults **Central Memory** for system instructions
3. Analyzes which agents are needed
4. Generates a multi-step JSON plan
5. Routes tasks to appropriate specialists
6. Supports **sequential** or **parallel** execution

### Intelligent Routing
The Orchestrator uses the LLM to match tasks to agents based on:
- Agent capability descriptions
- Task keywords and context
- Historical success patterns (stored in Central Memory)

### Example Routing
**Query**: "Check my system health and backup the database"

**Plan**:
```json
{
  "steps": [
    {"id": 1, "agent": "SysAgent", "task": "check RAM and disk usage"},
    {"id": 2, "agent": "DatabaseAgent", "task": "backup database to /backups"}
  ]
}
```

---

## Execution Modes

### Sequential (Default)
```python
results = orchestrator.run("check RAM and ping google")
```
Agents execute one after another. Safe and predictable.

### Parallel (Async)
```python
results = await orchestrator.run_async("check RAM and ping google")
```
Independent agents run concurrently for faster execution.

---

## Adding New Agents

LIA's architecture makes it trivial to add new specialists:

1. **Create a new agent file** in `agents/`
2. **Inherit from `LIAAgent`**
3. **Register tools** in `__init__`
4. **Implement `execute()`** method
5. **Add to the swarm** in `lia.py`

**Example**:
```python
from agents.base_agent import LIAAgent

class WeatherAgent(LIAAgent):
    def __init__(self):
        super().__init__("WeatherAgent", ["Weather forecasts", "Climate data"])
        self.register_tool("get_weather", self.get_weather, "Gets weather for a city")
    
    def get_weather(self, city: str):
        # Implementation here
        pass
    
    def execute(self, task: str) -> str:
        # LLM-based tool selection
        pass
```

Then add to `lia.py`:
```python
agents = [
    FileAgent(),
    SysAgent(),
    # ... other agents
    WeatherAgent()  # New agent automatically integrated
]
```

The Orchestrator will automatically discover and use the new agent!

---

## Agent Communication

Agents can share context through:
- **Central Memory**: Store/retrieve cross-session data
- **Audit Logs**: Review what other agents have done
- **Workflow Variables**: Pass data between steps

**Example Workflow with Data Passing**:
```yaml
steps:
  - id: 1
    agent: "FileAgent"
    task: "find the latest backup file"
  - id: 2
    agent: "DatabaseAgent"
    task: "restore from {{backup_file}}"
```
