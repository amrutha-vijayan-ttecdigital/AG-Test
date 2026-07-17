#!/usr/bin/env python3
"""
generate_profile.py — Scaffold profiles.json and .env connection credentials automatically.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""

def main():
    parser = argparse.ArgumentParser(description="Generate profiles.json and .env onboarding files.")
    parser.add_argument("--project", help="GCP Project ID (defaults to active gcloud project)")
    parser.add_argument("--agent-id", help="GCP Dialogflow CX / CES Agent ID")
    parser.add_argument("--location", default="us-central1", help="GCP region location (default: us-central1)")
    parser.add_argument("--dry-run", action="store_true", help="Print configuration without writing files")
    args = parser.parse_args()

    # Detect workspace root
    curr = Path.cwd()
    workspace_root = None
    for p in [curr] + list(curr.parents):
        if (p / "dfcx-starter-kit").is_dir() or (p / "ces-agent-studio-starter-kit").is_dir():
            workspace_root = p
            break
    if not workspace_root:
        workspace_root = curr

    # Resolve active GCP details
    project = args.project or run_cmd("gcloud config get-value project") or "your-gcp-project-id"
    gcv_account = run_cmd("gcloud config get-value account") or "your.email@domain.com"
    agent_id = args.agent_id or "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

    print(f"Detected GCP Active Project: {project}")
    print(f"Detected Active account: {gcv_account}")

    dfcx_base = workspace_root / "dfcx-starter-kit"
    ces_base = workspace_root / "ces-agent-studio-starter-kit"

    # 1. Dialogflow CX Profile Setup
    if dfcx_base.is_dir():
        profile_tpl = dfcx_base / "dialogflowcx" / "profiles.example.json"
        profile_out = dfcx_base / "dialogflowcx" / "profiles.json"
        
        if profile_tpl.is_file():
            print(f"Scaffolding DFCX profiles.json at {profile_out.relative_to(workspace_root)}")
            
            # Construct a basic profile configuration
            profile_data = {
                "default": {
                    "project_id": project,
                    "location_id": args.location,
                    "agent_id": agent_id,
                    "account": gcv_account
                }
            }
            
            if args.dry_run:
                print(f"[DRY-RUN] Would write DFCX profiles.json:\n{json.dumps(profile_data, indent=2)}")
            else:
                profile_out.parent.mkdir(parents=True, exist_ok=True)
                with open(profile_out, "w", encoding="utf-8") as f:
                    json.dump(profile_data, f, indent=2)
                print(f"Successfully generated: {profile_out}")

    # 2. CX Agent Studio .env Setup
    if ces_base.is_dir():
        env_tpl = ces_base / ".env.example"
        env_out = ces_base / ".env"
        
        if env_tpl.is_file():
            print(f"Scaffolding CES .env at {env_out.relative_to(workspace_root)}")
            
            env_content = f"""# Google Cloud Connection Details
GCP_PROJECT_ID={project}
GCP_REGION={args.location}

# CX Agent Studio Configuration
CES_AGENT_ID={agent_id}
DEVELOPER_EMAIL={gcv_account}
"""
            if args.dry_run:
                print(f"[DRY-RUN] Would write CES .env:\n{env_content}")
            else:
                with open(env_out, "w", encoding="utf-8") as f:
                    f.write(env_content)
                print(f"Successfully generated: {env_out}")

    print("\nOnboarding setup complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
