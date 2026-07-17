---
name: practitest
description: Query and update PractiTest test cases, instances, and runs. Invoke when the user says "check practitest", "pull practitest tests", "update practitest", "sync practitest", "practitest status", "qa management", or "find test in practitest".
---

# PractiTest

Helper for the PractiTest test management system. Use this skill when the team asks "what's failing in PractiTest", "did this test get run", "find the test for X", or "push our automated results into PractiTest".

## Setup

Creds live in `.env`:

```
PRACTITEST_API_KEY=...
PRACTITEST_PROJECT_ID=YOUR_PROJECT_ID
PRACTITEST_FILTER_ID=YOUR_FILTER_ID
PRACTITEST_EMAIL=your-email@domain.com
```

PractiTest uses HTTP Basic auth where the username is the developer email and the password is the API token.

## Tool

All operations go through `.agents/scripts/practitest_client.py`. It loads `.env` automatically, paginates list endpoints, and exposes both a Python class (`PractiTestClient`) and a CLI.

### CLI quick reference

```bash
# List tests in the configured filter
python3 .agents/scripts/practitest_client.py ls

# Show a specific test (preconditions, custom fields, run-status)
python3 .agents/scripts/practitest_client.py show <TEST_ID>

# Steps inside a test (positions, names, expected results)
python3 .agents/scripts/practitest_client.py steps <TEST_ID>

# Keyword search across name + description + tags
python3 .agents/scripts/practitest_client.py search "autopay"

# List runs for a specific test
python3 .agents/scripts/practitest_client.py runs --test-id <TEST_ID>

# Mark a run PASSED/FAILED on an instance (test must be added to a Test Set first)
python3 .agents/scripts/practitest_client.py push-result \
    --test-id <TEST_ID> --status PASSED --note "auto-replay run"
```

### Python usage

```python
from practitest_client import PractiTestClient
pt = PractiTestClient.from_env()

# All tests in the configured filter
tests = pt.list_tests()
print(f'{len(tests)} tests')

# Find balance-related tests
hits = pt.search_tests("balance")

# Update a run (instance_id must come from list_instances)
pt.create_run(instance_id=12345, status="PASSED", note="auto-replay run")
```

## Common workflows

### 1. Check current status of tests in the filter

```bash
python3 .agents/scripts/practitest_client.py ls | head -30
```

Look at the second column — `NO RUN` / `PASSED` / `FAILED` shows current state.

### 2. Find the PractiTest test for a keyword or intent

```bash
python3 .agents/scripts/practitest_client.py search "set up autopay"
# or
python3 .agents/scripts/practitest_client.py search "PIN"
```

If nothing matches, the test may be in a different filter. Pull a different filter:

```bash
python3 .agents/scripts/practitest_client.py ls --filter <other-id>
```

### 3. Push automated test results into PractiTest

Use `search_tests()` to find the PractiTest test that matches each automated case, then push the result via `create_run`.

```python
from practitest_client import PractiTestClient
pt = PractiTestClient.from_env()

import json
results = json.load(open("logs/replay/results.json"))

for r in results:
    name = r["name"]
    keyword = name.split("/")[-1].strip()
    matches = pt.search_tests(keyword)
    if not matches:
        print(f"  no PractiTest match for {name!r}")
        continue
    test_id = matches[0]["id"]
    instances = pt.list_instances(test_id=test_id, max_pages=2)
    if not instances:
        print(f"  test {test_id} ({name}) has no instances — needs to be added to a Test Set")
        continue
    pt.create_run(
        instance_id=instances[0]["id"],
        status="PASSED" if r["ok"] else "FAILED",
        note=f"automated replay {len(r['failures'])} failures" if not r["ok"] else "automated replay PASS",
    )
```

### 4. Audit which PractiTest tests have never been run

```bash
python3 .agents/scripts/practitest_client.py ls 2>&1 | awk '$2 == "NO" {print}' | head -20
```

### 5. Show steps and preconditions for a test ID

```bash
python3 .agents/scripts/practitest_client.py show <TEST_ID>
python3 .agents/scripts/practitest_client.py steps <TEST_ID>
```

## Notes

- **Run creation** requires a test **instance**, not a raw test ID. Instances live inside Test Sets. If a test isn't in any Set, `push-result` will fail with "no instance found" — ask QA to add it to a Set first, or use the `list_sets` / `list_instances` helpers to find an existing one.
- **Pagination**: list endpoints return up to 100 per page; the client auto-paginates up to 20 pages (2000 results).
- **Status values**: `PASSED`, `FAILED`, `BLOCKED`, `N/A`, `NO RUN`.
- **API base**: `https://api.practitest.com/api/v2/` — full docs at https://www.practitest.com/api-v2/.
