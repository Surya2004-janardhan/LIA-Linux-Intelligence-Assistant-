# LIA Workflows Guide

## What are Workflows?

Workflows are **multi-agent automation routines** defined in YAML. They allow you to chain together multiple tasks across different agents without writing code.

---

## YAML Structure

```yaml
name: "Workflow Name"
description: "What this workflow does"
steps:
  - id: 1
    agent: "AgentName"
    task: "Natural language task description"
  - id: 2
    agent: "AnotherAgent"
    task: "Another task, can reference {{variables}}"
```

---

## Example: Friday Routine

**File**: `workflows/friday_routine.yaml`

```yaml
name: "Friday Night Routine"
description: "Organize week, backup system info, and check connectivity."
steps:
  - id: 1
    agent: "FileAgent"
    task: "create a directory named 'weekly_backup'"
  - id: 2
    agent: "SysAgent"
    task: "check my ram usage"
  - id: 3
    agent: "NetAgent"
    task: "ping google.com to check connectivity"
  - id: 4
    agent: "WebAgent"
    task: "open https://github.com"
```

**Run it**:
```bash
python lia.py run friday_routine
```

---

## Variable Substitution

You can use variables in your workflows:

```yaml
steps:
  - id: 1
    agent: "FileAgent"
    task: "move {{source_file}} to {{dest_folder}}"
```

Then pass variables when running:
```python
workflow_engine.execute_workflow("my_workflow", variables={
    "source_file": "report.pdf",
    "dest_folder": "Archive"
})
```

---

## Creating Custom Workflows

1. Create a new `.yaml` file in the `workflows/` directory
2. Follow the structure above
3. Use any of the 6 agents: FileAgent, SysAgent, GitAgent, NetAgent, WebAgent, ConnectionAgent
4. Test with `python lia.py run your_workflow_name`

---

## Workflow Marketplace (Coming Soon)

LIA will support importing/exporting workflows to share with the community:
- Export: `lia.py export friday_routine`
- Import: `lia.py import community_workflow.yaml`

---

## Advanced: Conditional Steps

Future versions will support conditional execution:
```yaml
steps:
  - id: 1
    agent: "SysAgent"
    task: "check disk space"
    on_success: 2
    on_failure: 3
```
