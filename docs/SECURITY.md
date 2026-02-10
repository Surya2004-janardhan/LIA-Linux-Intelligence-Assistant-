# LIA Security Model

## Principles

1. **Local-First**: All processing happens on your machine. No telemetry, no cloud calls unless you explicitly enable a Connection.
2. **Deny by Default**: External integrations (Gmail, Calendar) are OFF until toggled ON.
3. **Least Privilege**: Agents can only access whitelisted directories. System paths are always blocked.
4. **Full Audit Trail**: Every action is logged with timestamp, agent, task, result, and status.

---

## Permission Manager

**File**: `core/permissions.py`

### Path Whitelisting
Agents can only access directories listed in `config.yaml`:
```yaml
permissions:
  allowed_paths:
    - "~/Documents"
    - "~/Downloads"
    - "~/Desktop"
    - "."  # Current working directory
```

### Path Blacklisting (Always Blocked)
These paths are hardcoded and cannot be overridden:
- `/etc`, `/boot`, `/root`, `/var/log` (Linux)
- `C:\Windows`, `C:\Users\Default` (Windows)

### How It Works
```python
# Every file operation checks:
if not permission_manager.is_path_allowed(path):
    return "Permission Denied"
```

The check resolves to absolute paths, so `../../../etc/passwd` won't bypass the whitelist.

---

## Connection Kill-Switches

**File**: `core/permissions.py`

External service access is controlled via config:
```yaml
connections:
  gmail_enabled: false
  calendar_enabled: false
  custom_api_enabled: false
```

If disabled, the ConnectionAgent returns a clear error:
```
"Connection Disabled: Gmail integration is OFF. Enable it in Settings > Connections."
```

---

## Database Safety

The `DatabaseAgent` enforces **SELECT-only queries**:
```python
if not query.strip().upper().startswith("SELECT"):
    return "Safety: Only SELECT queries are allowed."
```

Write operations must be performed through dedicated tools, never through raw SQL.

---

## Audit Trail

**File**: `core/audit.py`  
**Database**: `memory/audit_log.db`

Every agent action is recorded:
| Field | Description |
|-------|-------------|
| timestamp | When the action occurred |
| agent | Which agent executed it |
| task | What was requested |
| result | What happened (capped at 2KB) |
| status | success / error |
| tokens_used | LLM tokens consumed |

### View Audit Stats
```python
from core.audit import audit_manager
stats = audit_manager.get_agent_stats()
# Returns: [{"agent": "FileAgent", "tasks": 42, "tokens": 3500}, ...]
```

---

## Subprocess Safety

All agents that run shell commands use:
- **Timeout protection**: `subprocess.run(cmd, timeout=15)` prevents hangs
- **Capture output**: `capture_output=True` prevents terminal pollution
- **OS detection**: Windows vs Linux commands are handled automatically

---

## Sandboxing (Linux)

**File**: `core/sandbox.py`

When enabled, commands are wrapped in Firejail:
```python
if sandbox_enabled and os.name != 'nt':
    cmd = ["firejail", "--quiet"] + cmd
```

Enable via config:
```yaml
security:
  sandbox_enabled: true
```

---

## Token Cost Control

The two-tier routing system in `base_agent.py` is also a security feature:
- **Tier 1 (keywords)**: No LLM call = no prompt injection risk
- **Tier 2 (LLM)**: Uses compact prompts with JSON-only output format

This means ~70% of agent tasks never touch the LLM, reducing the attack surface for prompt injection.

---

## Security Checklist

- [x] Path whitelisting/blacklisting
- [x] Connection kill-switches (deny by default)
- [x] SELECT-only database queries
- [x] Subprocess timeout protection
- [x] Full audit trail with token tracking
- [x] Firejail sandboxing (Linux)
- [x] OS-level permission error handling
- [x] Result size capping (2KB) to prevent DB bloat
- [x] No hardcoded credentials
- [x] Config write-back for runtime settings changes
