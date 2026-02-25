# WIA Agent Ecosystem

WIA uses a **Dynamic Multi-Agent Swarm**. Agents are auto-discovered by the Orchestrator — add a new one and it's immediately available for routing.

---

## Smart Routing (How Agents Save Tokens)

Every agent uses a **two-tier execution model** inherited from `base_agent.py`:

```
Task arrives at agent
    │
    ├─ Tier 1: Keyword match (0 tokens, instant)
    │     "check RAM" → matches keyword "ram" → calls check_ram()
    │
    └─ Tier 2: LLM fallback (~200 tokens, 1-3 seconds)
          "how much memory is my node process using" → ambiguous → ask LLM
```

**Result**: ~70% of tasks hit Tier 1. A typical 3-step workflow costs ~300 tokens instead of ~2300.

---

## Agent Registry

### FileAgent
**Domain**: Filesystem  
**Tools**: list_directory, move_file, create_directory, find_files  
**Keywords**: list, ls, dir, move, mv, mkdir, find, search, locate  
**Security**: Permission-aware (whitelist only)

### SysAgent
**Domain**: System monitoring  
**Tools**: check_cpu, check_ram, check_disk, manage_service, system_health  
**Keywords**: cpu, ram, memory, disk, storage, health, service  
**Bonus**: `system_health` returns CPU+RAM+Disk in 1 call (saves 3 separate calls)

### GitAgent
**Domain**: Version control  
**Tools**: git_status, git_commit, git_log, git_diff, gh_pr_list  
**Keywords**: status, commit, log, history, diff, pr, pull request

### NetAgent
**Domain**: Network  
**Tools**: ping_host, check_ports, check_connectivity  
**Keywords**: ping, port, scan, internet, connectivity  
**OS-Layer**: Uses Python `socket` for port scanning when nmap isn't installed. Uses `socket.create_connection` for instant connectivity checks (no subprocess).

### WebAgent
**Domain**: Browser  
**Tools**: open_url, google_search  
**Keywords**: open, launch, visit, search, google  
**Smart**: Auto-adds `https://` if protocol missing

### ConnectionAgent
**Domain**: 3rd-party integrations  
**Tools**: check_gmail, send_draft, check_calendar  
**Keywords**: email, gmail, inbox, calendar, schedule  
**Security**: All disabled by default. Returns clear error message pointing to Settings.

### DockerAgent
**Domain**: Containers  
**Tools**: list_containers, start_container, stop_container, compose_up  
**Keywords**: containers, docker ps, docker start/stop, compose  
**Safety**: Timeout protection on all subprocess calls

### DatabaseAgent
**Domain**: SQL operations  
**Tools**: query_sqlite, backup_db, list_tables  
**Keywords**: query, select, sql, tables, backup, schema  
**Safety**: SELECT-only enforcement — no DROP, DELETE, UPDATE via agent

### PackageAgent
**Domain**: Package management  
**Tools**: install_pip, install_npm, list_pip, update_system  
**Keywords**: pip, npm, install, update system, python package

---

## Adding a New Agent

**Time required**: ~5 minutes

```python
# agents/weather_agent.py
from agents.base_agent import WIAAgent
from core.logger import logger

class WeatherAgent(WIAAgent):
    def __init__(self):
        super().__init__("WeatherAgent", ["Weather forecasts"])
        self.register_tool("get_weather", self.get_weather, 
            "Gets weather for a city",
            keywords=["weather", "forecast", "temperature"])

    def get_weather(self, city: str = "London"):
        # Your implementation
        return f"Weather in {city}: 22°C, Sunny"

    def extract_args_from_task(self, task: str, tool_name: str) -> dict:
        import re
        match = re.search(r'(?:in|for|at)\s+(\w+)', task, re.I)
        return {"city": match.group(1) if match else "London"}

    def execute(self, task: str) -> str:
        logger.info(f"WeatherAgent: {task}")
        return self.smart_execute(task)
```

Then in `WIA.py`:
```python
from agents.weather_agent import WeatherAgent

agents = [
    ...existing agents...
    WeatherAgent()  # Auto-discovered by Orchestrator
]
```

**That's it.** The Orchestrator's system prompt auto-generates from registered agents. No need to update routing rules, docs, or prompts.

---

## Agent Communication

Agents share context through:
1. **Central Memory**: `central_memory.store("last_backup", "/backups/today.tar.gz")`
2. **Audit Trail**: Review what other agents have done
3. **Workflow Variables**: Pass data between steps with `{{variable}}` syntax
