import os
import sys
import re
import datetime

LOG_RULE_CONTENT = """
## Governance Log (`agent.changes.log`)
Every side-effecting change (files, resources, tool runs) must be appended to `agent.changes.log` at the project root. This log is **append-only**; never edit, delete, or truncate existing entries.
- **Initialization**: Create the log as your first action if it does not exist.
- **Entry Format**: `YYYY-MM-DD HH:MM:SS GMT | <author> | <action> | <path/scope> | <summary>`
  - Indent detail blocks (2 spaces) for: failures, retries, multi-file changes, `GRANT`/`REVOKE` context, or non-routine `RUN` outcomes.
- **Author**: `<agent>:<version>` (e.g., `antigravity:gemini-3.5-flash`) or human username.
- **Actions**: `CREATE`, `EDIT`, `DELETE`, `MOVE`, `RENAME`, `RESTORE`, `GRANT`, `REVOKE`, `RUN`.
- **Scope**: Log all state-changing actions (file edits, tool side-effects). **Do NOT** log every conversation turn, reading, or scratch work. Skip failures that leave no trace.
"""

def setup_log(target_dir="."):
    # Look for rule files in target_dir and target_dir/.agents
    paths = [
        os.path.join(target_dir, ".agents", "AGENTS.md"),
        os.path.join(target_dir, ".agents", "CLAUDE.md"),
        os.path.join(target_dir, ".agents", "GEMINI.md"),
        os.path.join(target_dir, "AGENTS.md"),
        os.path.join(target_dir, "CLAUDE.md"),
        os.path.join(target_dir, "GEMINI.md"),
    ]
    
    found_file = None
    for p in paths:
        if os.path.exists(p):
            found_file = p
            break
            
    if not found_file:
        # Default to creating .agents/AGENTS.md
        os.makedirs(os.path.join(target_dir, ".agents"), exist_ok=True)
        found_file = os.path.join(target_dir, ".agents", "AGENTS.md")
        with open(found_file, "w") as f:
            f.write("# Workspace Rules\n")
        print(f"Created new rules file: {found_file}")

    with open(found_file, "r") as f:
        content = f.read()

    if "agent.changes.log" in content:
        print(f"Governance log section already exists in {found_file}")
        return

    # Find the last section number if AGENTS.md uses them
    # e.g., "## 8. Something"
    sections = re.findall(r"^##\s+(\d+)\.", content, re.MULTILINE)
    next_num = ""
    if sections:
        last_num = max(int(n) for n in sections)
        next_num = f"{last_num + 1}. "

    # Append to file
    with open(found_file, "a") as f:
        # Ensure we have clean spacing
        if not content.endswith("\n\n"):
            f.write("\n\n")
        f.write("---\n\n")
        f.write(f"## {next_num}Governance Log (`agent.changes.log`)\n")
        # Write the rest of the content (excluding the title line)
        lines = LOG_RULE_CONTENT.strip().split("\n")[1:]
        f.write("\n".join(lines) + "\n")

    print(f"Successfully added Governance Log to {found_file}")
    
    # Initialize the log file
    log_path = os.path.join(target_dir, "agent.changes.log")
    if not os.path.exists(log_path):
        with open(log_path, "w") as f:
            now_gmt = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S GMT")
            f.write(f"{now_gmt} | system | CREATE | agent.changes.log | Initialized governance log.\n")
        print(f"Initialized log file: {log_path}")

if __name__ == "__main__":
    target = "."
    if len(sys.argv) > 1:
        target = sys.argv[1]
    
    if not os.path.isdir(target):
        print(f"Error: {target} is not a valid directory.")
        sys.exit(1)
        
    setup_log(target)
