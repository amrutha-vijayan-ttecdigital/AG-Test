#!/usr/bin/env python3
"""
ces_replay.py — Interactive Conversational Agent Studio (CES) conversation history viewer and replay tool.
Fetches conversation logs from the Google Cloud CES API, displays turns, and replays them as fresh sessions.
"""

import argparse
import json
import pathlib
import sys
import uuid
from typing import Any, Dict, List

# Add the shared CES client directory to the Python path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / ".agents" / "scripts"))

try:
    from ces_client import CES, load_env, short
except ImportError as exc:
    print(f"ERROR: Cannot import ces_client. Ensure you run this from the starter kit directory: {exc}", file=sys.stderr)
    sys.exit(1)


def parse_conversation_turns(convo: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse v1/v1beta conversation logs to extract clean user/agent turns."""
    turns = []
    # CES uses 'turns' or 'interactions' or 'messages' depending on the API version
    raw_turns = convo.get("turns") or convo.get("interactions") or convo.get("messages") or []
    
    for idx, t in enumerate(raw_turns):
        user_input = ""
        agent_output = ""
        tool_calls = []
        route = []
        
        # 1. Parse User Input
        req = t.get("request") or t.get("userInput") or {}
        if isinstance(req, str):
            user_input = req
        else:
            user_input = (
                req.get("text") or 
                req.get("queryInput", {}).get("text", {}).get("text") or 
                req.get("input", {}).get("text", {}).get("text") or
                ""
            )
            # Check for event inputs
            if not user_input and "event" in req:
                user_input = f"[Event: {req['event'].get('event')}]"
            elif not user_input and "dtmf" in req:
                user_input = f"[DTMF: {req['dtmf'].get('digits')}]"

        # 2. Parse Agent Output & Diagnostics
        resp = t.get("response") or t.get("agentOutput") or {}
        if isinstance(resp, str):
            agent_output = resp
        else:
            outputs = resp.get("outputs") or resp.get("responseMessages") or []
            texts = []
            for out in outputs:
                if out.get("text"):
                    # CES REST response shape
                    texts.append(out["text"])
                elif isinstance(out.get("text"), dict) and out["text"].get("text"):
                    # DFCX/Proto response shape
                    texts.append(out["text"]["text"][0])
                
                # Check for diagnostic info (routes, tool calls)
                diag = out.get("diagnosticInfo", {})
                for msg in diag.get("messages", []):
                    role = msg.get("role", "")
                    if role and role not in {"user", "model", "system"} and role not in route:
                        route.append(role)
                    for chunk in msg.get("chunks", []):
                        tc = chunk.get("toolCall", {})
                        if tc.get("displayName"):
                            tool_calls.append(tc["displayName"])

            agent_output = " ".join(texts)

        turns.append({
            "index": idx,
            "user": user_input,
            "agent": agent_output,
            "tools": tool_calls,
            "route": route,
            "variables": t.get("variables", {}),
            "raw": t
        })
    return turns


def list_recent_conversations(c: CES, limit: int) -> None:
    """Fetch and print recent conversations in a clean list."""
    print("Fetching recent conversations...")
    try:
        convos = c.list("conversations")
    except Exception as e:
        print(f"API Error: Failed to retrieve conversations: {e}", file=sys.stderr)
        print("Tip: Make sure you run './setup.sh' to configure your .env file with active IDs.", file=sys.stderr)
        sys.exit(1)

    if not convos:
        print("No recent conversations found for this app.")
        return

    print("=" * 70)
    print(f"{'CONVERSATION ID':<25} | {'START TIME':<25} | {'DURATION':<10}")
    print("=" * 70)
    for convo in convos[:limit]:
        cid = short(convo.get("name"))
        start_time = convo.get("startTime", "unknown")[:19].replace("T", " ")
        duration = convo.get("duration", "0s")
        print(f"{cid:<25} | {start_time:<25} | {duration:<10}")
    print("=" * 70)


def show_conversation(c: CES, conversation_id: str, replay: bool = False) -> None:
    """Fetch and render conversation turns, optionally replaying them against the draft agent."""
    print(f"Fetching conversation details for: {conversation_id}...")
    try:
        convo = c.get("conversations", conversation_id)
    except Exception as e:
        print(f"Error: Failed to retrieve conversation '{conversation_id}': {e}", file=sys.stderr)
        sys.exit(1)

    turns = parse_conversation_turns(convo)
    if not turns:
        print("No turns found in this conversation. Raw payload:")
        print(json.dumps(convo, indent=2))
        return

    print("=" * 60)
    print(f"CONVERSATION: {conversation_id}")
    print(f"Start Time:   {convo.get('startTime', 'unknown')}")
    print(f"Duration:     {convo.get('duration', '0s')}")
    print("=" * 60)

    for turn in turns:
        print(f"\n[Turn {turn['index'] + 1}]")
        print(f"  User:   {turn['user']}")
        print(f"  Agent:  {turn['agent']}")
        if turn["tools"]:
            print(f"  Tools:  {', '.join(turn['tools'])}")
        if turn["route"]:
            print(f"  Route:  {' -> '.join(turn['route'])}")

    if not replay:
        return

    # Replay Loop
    print("\n" + "=" * 60)
    print("REPLAYING CONVERSATION AGAINST ACTIVE DRAFT AGENT")
    print("=" * 60)
    session_id = f"replay-{uuid.uuid4().hex[:12]}"
    
    # Track variables across the replay session
    current_vars = {}

    for turn in turns:
        user_input = turn["user"]
        if user_input.startswith("[Event:") or user_input.startswith("[DTMF:"):
            print(f"\nSkipping non-text turn: {user_input}")
            continue

        print(f"\n[Turn {turn['index'] + 1} Replay]")
        print(f"  User Input:   {user_input}")
        
        # Merge initial variables from original log on first turn if they exist
        if turn["index"] == 0 and turn["variables"]:
            current_vars.update(turn["variables"])

        try:
            resp = c.run_session(
                session_id=session_id,
                text=user_input,
                variables=current_vars if turn["index"] == 0 else None
            )
            
            # Parse response
            texts = []
            tools = []
            route = []
            for out in resp.get("outputs", []):
                if out.get("text"):
                    texts.append(out["text"])
                diag = out.get("diagnosticInfo", {})
                for msg in diag.get("messages", []):
                    role = msg.get("role", "")
                    if role and role not in {"user", "model", "system"} and role not in route:
                        route.append(role)
                    for chunk in msg.get("chunks", []):
                        tc = chunk.get("toolCall", {})
                        if tc.get("displayName"):
                            tools.append(tc["displayName"])

            replayed_output = " ".join(texts)
            print(f"  Orig Agent:   {turn['agent']}")
            print(f"  New Agent:    {replayed_output}")
            if tools:
                print(f"  New Tools:    {', '.join(tools)}")
            if route:
                print(f"  New Route:    {' -> '.join(route)}")

            # Compare differences
            if replayed_output.strip() != turn["agent"].strip():
                print("  [DIFF] Responses differ from original log.")
                
        except Exception as e:
            print(f"  [ERROR] Replay failed: {e}", file=sys.stderr)
            break

    print("\nReplay session complete.")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive Conversational Agent Studio (CES) conversation history viewer and replay tool."
    )
    parser.add_argument(
        "conversation_id",
        nargs="?",
        help="ID of the conversation to inspect/replay. If omitted, lists recent conversations."
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=15,
        help="Number of conversations to list (default: 15)"
    )
    parser.add_argument(
        "--replay", "-r",
        action="store_true",
        help="Replay conversation turns as a fresh session against the active draft agent"
    )
    parser.add_argument(
        "--beta",
        action="store_true",
        help="Use the v1beta API surface"
    )

    args = parser.parse_args()

    # Load environment variables to ensure requirements exist
    env = load_env(require=True)
    c = CES(env=env, beta=args.beta)

    if not args.conversation_id:
        list_recent_conversations(c, args.limit)
    else:
        show_conversation(c, args.conversation_id, args.replay)


if __name__ == "__main__":
    main()
