---
name: jira-stories
description: "Generate Jira user stories from an agent_design.md — groups by agent, guardrails, and test validation into manageable stories under an Epic"
allowed-tools: Bash(python*), Read, Grep
---

# Generate Jira Stories from Agent Design

Reads an agent design markdown file and creates Jira user stories grouped into manageable chunks.

## How to Use

- `/jira-stories` — lists designs in `agents/` folder, prompts which to use
- `/jira-stories agents/your_design.md` — reads a specific design file
- `/jira-stories --dry-run` — show stories without creating them
- Template for new designs: `agents/TEMPLATE.md`

## Grouping Strategy

Agent Studio CX agents follow a consistent pattern: root agent with children, each having tools and callbacks. Instead of one story per tool (too granular), group into actionable stories:

### 1. One story per agent
Each agent story includes its tools, callbacks, and key behaviors as acceptance criteria.
- **Summary:** "Implement {agent_name} — {role}"
- **Description:** Role, in-scope capabilities, tools (as checklist), callbacks, key behaviors
- **Labels:** `agent:{agent_name}`, `type:implementation`

### 2. One story for all guardrails
- **Summary:** "Configure guardrails for {app_name}"
- **Description:** Each guardrail as a checklist item with type, trigger, and action
- **Labels:** `type:guardrail`

### 3. One story for E2E test validation
- **Summary:** "Validate E2E conversation flows for {app_name}"
- **Description:** Each flow path as acceptance criteria with expected tools and agent transfers
- **Labels:** `type:e2e-test`

### 4. One story for routing test validation
- **Summary:** "Validate agent routing and handoffs for {app_name}"
- **Description:** Each routing rule as acceptance criteria
- **Labels:** `type:routing-test`

This gives ~6 stories for a typical 3-agent app instead of 30+.

## API Pattern

```python
import os, requests, json
from dotenv import load_dotenv
load_dotenv()

SITE = os.getenv("JIRA_SITE")
USER = os.getenv("JIRA_USER")
TOKEN = os.getenv("JIRA_TOKEN")
PROJECT = os.getenv("JIRA_PROJECT", "YOUR_PROJECT_KEY")
BASE = f"https://{SITE}/rest/api/3"

def jira(method, path, **kwargs):
    r = requests.request(method, f"{BASE}/{path}", auth=(USER, TOKEN),
                         headers={"Accept": "application/json", "Content-Type": "application/json"}, **kwargs)
    return r.json() if r.text else {}
```

## Creating Stories with ADF

Jira Cloud uses Atlassian Document Format. For checklists in descriptions, use a task list:

```python
def make_checklist(items):
    """Build ADF taskList from a list of strings."""
    return {
        "type": "taskList",
        "attrs": {"localId": "1"},
        "content": [
            {"type": "taskItem", "attrs": {"localId": str(i), "state": "TODO"},
             "content": [{"type": "text", "text": item}]}
            for i, item in enumerate(items, 1)
        ]
    }

def create_story(summary, paragraphs, checklist_items=None, labels=None, epic_key=None):
    content = [{"type": "paragraph", "content": [{"type": "text", "text": p}]} for p in paragraphs]
    if checklist_items:
        content.append(make_checklist(checklist_items))
    fields = {
        "project": {"key": PROJECT},
        "issuetype": {"name": "Story"},
        "summary": summary[:255],
        "description": {"type": "doc", "version": 1, "content": content}
    }
    if labels:
        fields["labels"] = labels
    if epic_key:
        fields["parent"] = {"key": epic_key}
    return jira("POST", "issue", json={"fields": fields})
```

## Workflow

1. Read the design file
2. Parse the markdown into sections (agents, guardrails, flows)
3. Group into ~6 stories per the strategy above
4. For `--dry-run`: print stories as a table with acceptance criteria counts
5. Otherwise:
   a. Create an Epic: "{app_name} Implementation"
   b. Create each story linked to the Epic
   c. Report keys and summaries

## Example Output

```
Epic: PROJ-3 "Retail Agent Implementation"

  PROJ-4  Implement retail_agent — Product Pro     [agent:retail_agent]   (7 tools, 4 callbacks)
  PROJ-5  Implement upsell_agent — services        [agent:upsell_agent]   (6 tools, 1 callback)
  PROJ-6  Implement out_of_scope_handling — fallback       [agent:out_of_scope]    (1 tool)
  PROJ-7  Configure guardrails                             [type:guardrail]        (4 guardrails)
  PROJ-8  Validate E2E conversation flows                  [type:e2e-test]         (4 flows)
  PROJ-9  Validate agent routing and handoffs              [type:routing-test]     (4 routes)

Total: 6 stories under 1 epic
```

## Notes

- Check for existing stories with similar summaries before creating duplicates
- The agent reading this should parse the actual markdown structure, not hardcode values
- For larger apps (5+ agents), consider grouping child agents by function area
- Each story's acceptance criteria should be specific enough that a dev can implement without re-reading the full design
