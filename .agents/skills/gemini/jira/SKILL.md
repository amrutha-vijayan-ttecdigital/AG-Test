---
name: jira
description: "Manage Jira issues — create bugs from test failures, search, comment, transition, link to PractiTest"
allowed-tools: Bash(python*), Read, Grep
---

# Jira Issue Management

Manage Jira issues using the REST API.

Auth is in `.env` (`JIRA_SITE`, `JIRA_USER`, `JIRA_TOKEN`, `JIRA_PROJECT`). All calls use basic auth.

## How to Use

When the user says `/jira` with additional context, determine which workflow applies:
- `/jira` — open issue summary
- `/jira create bug for <Feature/Scenario>` — file a bug
- `/jira search scheduling` — keyword search
- `/jira comment <ISSUE_KEY> "fixed"` — add comment
- `/jira close <ISSUE_KEY>` — transition to done
- `/jira assign <ISSUE_KEY> <assignee_email_or_id>` — assign to team member
- `/jira reconcile` — compare test results vs open bugs, close fixed ones
- `/jira regressions` — find tests that were passing but now fail
- `/jira metrics` — open bug count, MTTR, flaky rate
- `/jira board` — sprint board summary

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

## PractiTest Helpers

Use these to pull test data for Jira workflows:

```python
PT_TOKEN = os.getenv("PRACTITEST_API_TOKEN")
PT_PROJECT = os.getenv("PRACTITEST_PROJECT_ID", "YOUR_PRACTITEST_PROJECT_ID")
PT_BASE = f"https://api.practitest.com/api/v2/projects/{PT_PROJECT}"
PT_HEADERS = {"PTToken": PT_TOKEN, "Content-Type": "application/json"}

def pt(method, path, **kwargs):
    r = requests.request(method, f"{PT_BASE}/{path}", headers=PT_HEADERS, **kwargs)
    return r.json() if r.text else {}
```

## Workflows

### 1. Create Bug from Test Failure

Before creating, search for existing open issues with the same test name to avoid duplicates. Always include PractiTest link.

```python
# Load PT mapping for cross-reference
mapping = json.load(open("practitest_mapping.json"))
pt_id = mapping.get(test_name, {}).get("test_id", "")
pt_url = f"https://prod.practitest.com/p/{PT_PROJECT}/tests/{pt_id}" if pt_id else ""

# Search for existing issue first
results = jira("GET", "search/jql", params={"jql": f'project={PROJECT} AND summary ~ "{test_name}" AND status != Done'})
if results.get("total", 0) > 0:
    issue_key = results["issues"][0]["key"]
    jira("POST", f"issue/{issue_key}/comment", json={
        "body": {"type": "doc", "version": 1, "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": f"Still failing. {error_details}"}]}
        ]}
    })
else:
    jira("POST", "issue", json={
        "fields": {
            "project": {"key": PROJECT},
            "issuetype": {"name": "Bug"},
            "summary": f"Agent test failure: {test_name}",
            "description": {"type": "doc", "version": 1, "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": f"Expected: {expected}"}]},
                {"type": "paragraph", "content": [{"type": "text", "text": f"Actual: {actual}"}]},
                {"type": "paragraph", "content": [{"type": "text", "text": f"PractiTest: {pt_url}"}]}
            ]}
        }
    })
```

### 2. Search Issues

```python
# Open issues
jira("GET", "search/jql", params={"jql": f"project={PROJECT} AND status != Done ORDER BY created DESC", "maxResults": 20})

# By keyword
jira("GET", "search/jql", params={"jql": f'project={PROJECT} AND text ~ "keyword"'})

# Bugs only
jira("GET", "search/jql", params={"jql": f"project={PROJECT} AND issuetype = Bug AND status != Done"})
```

### 3. Add Comment

```python
jira("POST", f"issue/{issue_key}/comment", json={
    "body": {"type": "doc", "version": 1, "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Comment text here"}]}
    ]}
})
```

### 4. Transition Issue (change status)

```python
# Get available transitions
transitions = jira("GET", f"issue/{issue_key}/transitions")
# Find the right transition ID, then:
jira("POST", f"issue/{issue_key}/transitions", json={"transition": {"id": transition_id}})
```

### 5. Reconcile — Close Fixed Bugs

Compare latest test results against open Jira bugs. When a test that previously failed now passes:

```python
# Get all open bugs
bugs = jira("GET", "search/jql", params={"jql": f"project={PROJECT} AND issuetype = Bug AND status != Done"})

# Load latest results
results = json.load(open("results.json"))
passing = {r["test_name"] for r in results["results"] if r["passed"]}

# For each open bug, check if the test now passes
for issue in bugs.get("issues", []):
    summary = issue["fields"]["summary"]
    # Extract test name from summary (after "Agent test failure: ")
    test_name = summary.replace("Agent test failure: ", "")
    if test_name in passing:
        # Comment that it's fixed
        jira("POST", f"issue/{issue['key']}/comment", json={
            "body": {"type": "doc", "version": 1, "content": [
                {"type": "paragraph", "content": [{"type": "text", "text": "Test now passing. Closing."}]}
            ]}
        })
        # Transition to Done
        transitions = jira("GET", f"issue/{issue['key']}/transitions")
        done = next((t for t in transitions.get("transitions", []) if t["name"].lower() in ("done", "closed", "resolved")), None)
        if done:
            jira("POST", f"issue/{issue['key']}/transitions", json={"transition": {"id": done["id"]}})
```

### 6. Test Status Dashboard

Pull PT test statuses and present as a Jira-friendly summary:

```python
tests = pt("GET", "tests.json", params={"page[size]": 100})
passed = failed = no_run = 0
failures = []
for t in tests.get("data", []):
    status = t["attributes"].get("run-status", "NO RUN")
    if status == "PASSED": passed += 1
    elif status == "FAILED":
        failed += 1
        failures.append(t["attributes"]["name"])
    else: no_run += 1

print(f"Tests: {passed} passed, {failed} failed, {no_run} not run")
for f in failures:
    print(f"  FAIL: {f}")
```

### 7. Assign to Owner

```python
# Look up account ID by email
users = jira("GET", "user/search", params={"query": email})
if users:
    account_id = users[0]["accountId"]
    jira("PUT", f"issue/{issue_key}/assignee", json={"accountId": account_id})
```

### 8. Label / Tag Issues

Use labels to categorize by agent, test layer, or failure type:

```python
# Add labels when creating
"labels": ["agent:<agent_name>", "layer:e2e", "auto-filed"]

# Update labels on existing issue
jira("PUT", f"issue/{issue_key}", json={
    "fields": {"labels": ["agent:<agent_name>", "flaky", "auto-filed"]}
})

# Search by label
jira("GET", "search/jql", params={"jql": f'project={PROJECT} AND labels = "flaky"'})
```

When creating bugs from test failures, auto-apply labels:
- `auto-filed` — always, marks it as automation-created
- `agent:{agent_name}` — from the test's `expect_route`
- `tool:{tool_name}` — from the test's `expect_tool` if the failure is tool-related
### 9. Link Related Issues

Group issues with the same root cause:

```python
# Link two issues (e.g. same root cause)
jira("POST", "issueLink", json={
    "type": {"name": "Relates"},  # or "Blocks", "Causes", "Duplicates"
    "inwardIssue": {"key": "PROJ-1"},
    "outwardIssue": {"key": "PROJ-2"}
})

# When bulk filing, if multiple failures share the same agent route or tool,
# link them together and note "likely same root cause" in the link comment
```

### 11. Regression Detection

Find tests that were passing in previous runs but now fail:

```python
import sqlite3

db = sqlite3.connect("data/test_results.db")
cursor = db.cursor()

# Get last 2 runs
cursor.execute("SELECT id FROM test_runs ORDER BY created_at DESC LIMIT 2")
run_ids = [r[0] for r in cursor.fetchall()]

if len(run_ids) == 2:
    current_run, previous_run = run_ids

    # Tests that passed before but fail now
    cursor.execute("""
        SELECT curr.test_name
        FROM test_results curr
        JOIN test_results prev ON curr.test_name = prev.test_name
        WHERE curr.run_id = ? AND prev.run_id = ?
          AND curr.passed = 0 AND prev.passed = 1
    """, (current_run, previous_run))

    regressions = [r[0] for r in cursor.fetchall()]

    if regressions:
        print(f"REGRESSIONS DETECTED ({len(regressions)}):")
        for name in regressions:
            print(f"  {name}")

        # File high-priority bugs for regressions
        for name in regressions:
            results = jira("GET", "search/jql", params={"jql": f'project={PROJECT} AND summary ~ "{name}" AND status != Done'})
            if results.get("total", 0) == 0:
                jira("POST", "issue", json={
                    "fields": {
                        "project": {"key": PROJECT},
                        "issuetype": {"name": "Bug"},
                        "priority": {"name": "High"},
                        "summary": f"REGRESSION: {name}",
                        "labels": ["regression", "auto-filed"],
                        "description": {"type": "doc", "version": 1, "content": [
                            {"type": "paragraph", "content": [{"type": "text", "text":
                                "This test was passing in the previous run but now fails. Likely a new breakage."}]}
                        ]}
                    }
                })
    else:
        print("No regressions — all previously passing tests still pass.")
```

### 11. Metrics

```python
import sqlite3
from datetime import datetime, timedelta

# Open bugs over time
bugs = jira("GET", "search/jql", params={
    "jql": f"project={PROJECT} AND issuetype = Bug ORDER BY created ASC",
    "maxResults": 100
})
issues = bugs.get("issues", [])

open_count = sum(1 for i in issues if i["fields"]["status"]["name"] != "Done")
closed_count = sum(1 for i in issues if i["fields"]["status"]["name"] == "Done")
total = len(issues)

print(f"Bugs: {total} total, {open_count} open, {closed_count} closed")

# MTTR (mean time to resolve) for closed bugs
resolved_times = []
for i in issues:
    if i["fields"]["status"]["name"] == "Done":
        created = datetime.fromisoformat(i["fields"]["created"].replace("Z", "+00:00"))
        updated = datetime.fromisoformat(i["fields"]["updated"].replace("Z", "+00:00"))
        resolved_times.append((updated - created).total_seconds() / 3600)

if resolved_times:
    avg_hours = sum(resolved_times) / len(resolved_times)
    print(f"MTTR: {avg_hours:.1f} hours average")

# Flaky rate
flaky_count = sum(1 for i in issues if "flaky" in i["fields"].get("labels", []))
if total > 0:
    print(f"Flaky rate: {flaky_count}/{total} ({flaky_count/total:.0%})")

# Auto-filed vs manual
auto = sum(1 for i in issues if "auto-filed" in i["fields"].get("labels", []))
print(f"Auto-filed: {auto}/{total}")
```

### 12. Sprint Board Summary

```python
# Get the active sprint
AGILE = f"https://{SITE}/rest/agile/1.0"

def agile(method, path, **kwargs):
    r = requests.request(method, f"{AGILE}/{path}", auth=(USER, TOKEN),
                         headers={"Accept": "application/json"}, **kwargs)
    return r.json() if r.text else {}

boards = agile("GET", "board", params={"projectKeyOrId": PROJECT})
board_id = boards.get("values", [{}])[0].get("id")

if board_id:
    sprints = agile("GET", f"board/{board_id}/sprint", params={"state": "active"})
    active = sprints.get("values", [{}])[0] if sprints.get("values") else None

    if active:
        sprint_issues = jira("GET", "search/jql", params={
            "jql": f"project={PROJECT} AND sprint = {active['id']}",
            "maxResults": 50
        })

        by_status = {}
        for i in sprint_issues.get("issues", []):
            status = i["fields"]["status"]["name"]
            by_status.setdefault(status, []).append(i["key"])

        print(f"Sprint: {active['name']}")
        for status, keys in by_status.items():
            print(f"  {status}: {len(keys)} — {', '.join(keys)}")
```
