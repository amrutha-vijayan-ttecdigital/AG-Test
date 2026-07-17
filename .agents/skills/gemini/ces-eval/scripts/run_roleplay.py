#!/usr/bin/env python3
"""Roleplay simulator dialogue loop and evaluation runner.

Interleaves a simulated customer (via Vertex AI Gemini REST API) and
an Agent Studio agent (via the CES REST client), then evaluates the completed
transcript against design specifications using Gemini.

Also supports a robust offline/dry-run mock mode (--mock) that simulates the
entire dialogue loop, transcript formatting, and LLM evaluation parsing locally.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from typing import Any

# Set up paths for sibling imports
_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
for parent in _HERE.parents:
    cand = parent / ".agents" / "scripts"
    if cand.is_dir():
        sys.path.insert(0, str(cand))
        break

from ces_client import CES
import assertions as A

# Prompt templates as requested
CUSTOMER_SYSTEM_PROMPT = """You are roleplaying as a customer calling a customer service hotline.
Your profile is:
- Name: {name}
- Mood/Persona: {mood}
- Goal: {goal}
- Constraints: {constraint}

Guidelines:
1. Stay in character at all times. Act naturally like a human. Do not explain that you are an AI.
2. Keep your responses brief and conversational (1-2 sentences), as if spoken on a phone.
3. If the agent resolves your goal or reaches a terminal point (like being transferred), you should end the conversation by including the tag '<hangup>' at the end of your message.
"""

EVALUATOR_SYSTEM_PROMPT = """You are a QA auditor reviewing a dialogue transcript between an automated customer service agent and a customer.
Evaluate if the agent followed the design spec and handled the customer context correctly.

Design Specification:
{design_spec}

Customer Profile:
- Name: {customer_name}
- Mood: {customer_mood}
- Goal: {customer_goal}
- Constraints: {customer_constraint}

Dialogue Transcript:
{transcript}

Analyze the dialogue:
1. Did the agent follow the required route path / sub-agent handoffs?
2. Did the agent invoke the correct tools matching customer requests?
3. Did the agent successfully resolve the customer's goal?
4. Did the agent respect the customer's constraints?
5. Did the agent handle the customer's mood appropriately?

Output your evaluation in JSON format matching this schema:
{{
  "passed": true,
  "reasoning": "Detailed justification of the score and verdict",
  "violations": ["List of spec or customer-handling violations, empty if none"],
  "goal_resolved": true,
  "agent_mood_handling_score": 5
}}
"""


def call_gemini(
    project_id: str,
    region: str,
    token: str,
    model_id: str,
    contents: list,
    system_instruction: str = None,
    json_mode: bool = False
) -> dict:
    """Invokes the Vertex AI Gemini REST API using urllib."""
    # Map global 'us' to 'us-central1'
    vertex_region = "us-central1" if region == "us" else region
    
    url = f"https://{vertex_region}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{vertex_region}/publishers/google/models/{model_id}:generateContent"
    
    body = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7 if not json_mode else 0.1,  # low temp for eval
        }
    }
    
    if system_instruction:
        body["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }
        
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"
        
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            resp_body = json.loads(response.read().decode("utf-8"))
            return resp_body
    except urllib.error.HTTPError as e:
        error_info = e.read().decode("utf-8")
        sys.stderr.write(f"Vertex AI API call failed: HTTP {e.code}\n{error_info}\n")
        raise


# ---- Offline Dry-Run Mocks ----

def run_session_mock(
    session_id: str,
    text: str | None = None,
    customer_goal: str = "",
    customer_name: str = "",
    customer_mood: str = "",
    customer_constraint: str = ""
) -> dict:
    """Mock CES session turns locally with realistic diagnostic traces."""
    text_lower = (text or "").lower()
    
    agent_text = ""
    route = ["router"]
    tools = []
    variables = {}
    
    name_lower = customer_name.lower().replace(" ", "")
    
    if text == "<event>session start</event>":
        agent_text = "Hello! Welcome to Customer Support. My name is Alex. How can I help you today?"
        route = ["router"]
    elif "hello, my name is" in text_lower:
        agent_text = f"I see you want to {customer_goal}. Before we proceed, I need to verify your account details. What is your email?"
        route = ["router", "billing"]
    elif "my email is" in text_lower or "@" in text_lower:
        agent_text = "Thank you. I've verified your account. Let me pull up your account summary."
        route = ["billing"]
        tools = ["get_account_summary"]
        variables = {"verified": True, "email": f"{name_lower}@example.com"}
    elif "execute" in text_lower or "cancel" in text_lower or "goal" in text_lower:
        agent_text = "I've processed your request. Since you want to cancel, I will update the call category and transfer you to a specialist."
        route = ["billing", "transfer"]
        tools = ["transfer_to_specialist"]
        variables = {"callType": "billing_dispute"}
    else:
        agent_text = "I understand. I will assist you with that request."
        route = ["billing"]
        
    messages = []
    for r in route:
        messages.append({
            "role": r,
            "chunks": [
                {
                    "toolCall": {"displayName": tools[0]} if tools else {},
                    "updatedVariables": variables
                }
            ]
        })
        
    resp = {
        "outputs": [
            {
                "text": agent_text,
                "diagnosticInfo": {
                    "messages": messages
                }
            }
        ]
    }
    return resp


def call_gemini_mock_customer(contents: list, name: str, mood: str, goal: str, constraint: str) -> str:
    """Mock customer persona responses locally based on current dialog turn index."""
    model_turns = [c for c in contents if c.get("role") == "model"]
    turn_idx = len(model_turns)
    
    if turn_idx == 0:
        return f"Hello, my name is {name}. I want to {goal}."
    elif turn_idx == 1:
        return f"I am feeling {mood}. My email is {name.lower().replace(' ', '')}@example.com. But {constraint}."
    elif turn_idx == 2:
        return f"Great. Can you execute my goal to {goal}? And remember: {constraint}."
    else:
        return f"Thank you for the help. <hangup>"


def call_gemini_mock_evaluator() -> str:
    """Mock LLM evaluator JSON response matching the required schema."""
    return json.dumps({
        "passed": True,
        "reasoning": "The agent correctly routed the customer from router to billing, verified account information, accessed the account summary, and set session callType to billing_dispute before transferring. Customer constraints were respected and mood was handled appropriately.",
        "violations": [],
        "goal_resolved": True,
        "agent_mood_handling_score": 5
    })


def clean_json_text(text: str) -> str:
    """Strip markdown code-block wrappers from JSON response if present."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description="CX Agent Studio Roleplay Simulator")
    ap.add_argument("--customer-context", required=True, help="Path to customer context JSON file")
    ap.add_argument("--design-spec", required=True, help="Path to design spec Markdown/text file")
    ap.add_argument("--model", default="gemini-3.1-flash-lite", help="Vertex AI model ID")
    ap.add_argument("--max-turns", type=int, default=8, help="Maximum number of turns")
    ap.add_argument("--output", help="Path to write the simulation transcript and evaluation results")
    ap.add_argument("--no-fakes", action="store_true", help="Disable tool fakes (real backends)")
    ap.add_argument("--deployed", action="store_true", help="Target CES_DEPLOYMENT_ID instead of the draft")
    ap.add_argument("--entry-agent", help="Start session at a specific sub-agent ID")
    ap.add_argument("--mock", action="store_true", help="Enable local offline/dry-run simulation mode")
    
    args = ap.parse_args()
    
    # 1. Load Files
    try:
        with open(args.customer_context, "r", encoding="utf-8") as f:
            customer_ctx = json.load(f)
    except Exception as e:
        sys.stderr.write(f"Error loading customer context from {args.customer_context}: {e}\n")
        return 1
        
    try:
        with open(args.design_spec, "r", encoding="utf-8") as f:
            design_spec_content = f.read()
    except Exception as e:
        sys.stderr.write(f"Error loading design spec from {args.design_spec}: {e}\n")
        return 1
        
    name = customer_ctx.get("name", "Valued Customer")
    mood = customer_ctx.get("mood", "calm")
    goal = customer_ctx.get("goal", "general inquiry")
    constraint = customer_ctx.get("constraint", "none")
    
    # 2. Setup CES client
    if args.mock:
        print("Running in OFFLINE MOCK MODE. No live API calls will be made.")
        c = CES(env={
            "GCP_PROJECT_ID": "mock-project",
            "CES_APP_ID": "mock-app-id",
            "GCP_REGION": "us",
            "CES_AGENT_ID": "mock-agent-id"
        })
    else:
        try:
            c = CES()
        except (Exception, SystemExit) as e:
            sys.stderr.write(f"Error initializing CES client: {e}\n")
            sys.stderr.write("To test offline without credentials, use the --mock flag.\n")
            return 1
            
    deployment_id = c.deployment_id if args.deployed else None
    use_fakes = not (args.no_fakes or args.deployed)
    
    # Print targets
    print(f"Customer Name: {name}")
    print(f"Customer Mood: {mood}")
    print(f"Customer Goal: {goal}")
    print("-" * 60)
    
    session_id = f"roleplay-{uuid.uuid4().hex[:12]}"
    contents: list[dict[str, Any]] = []
    transcript_turns: list[str] = []
    variables: dict[str, Any] = {}
    
    # 3. Retrieve Greeting / First Session Turn
    if args.mock:
        resp = run_session_mock(
            session_id,
            text="<event>session start</event>",
            customer_goal=goal,
            customer_name=name,
            customer_mood=mood,
            customer_constraint=constraint
        )
    else:
        resp = c.run_session(
            session_id,
            text="<event>session start</event>",
            deployment_id=deployment_id,
            use_tool_fakes=use_fakes,
            entry_agent=args.entry_agent
        )
        
    agent_text = A.extract_text(resp)
    contents.append({"role": "user", "parts": [{"text": agent_text}]})
    transcript_turns.append(f"Agent: {agent_text}")
    print(f"\033[92mAgent:\033[0m {agent_text}")
    
    # 4. Dialogue Loop
    for turn in range(args.max_turns):
        # A. Customer turn
        if args.mock:
            customer_text = call_gemini_mock_customer(contents, name, mood, goal, constraint)
        else:
            sys_inst = CUSTOMER_SYSTEM_PROMPT.format(name=name, mood=mood, goal=goal, constraint=constraint)
            gemini_resp = call_gemini(
                project_id=c.project,
                region=c.location,
                token=c._get_token(),
                model_id=args.model,
                contents=contents,
                system_instruction=sys_inst
            )
            try:
                customer_text = gemini_resp["candidates"][0]["content"]["parts"][0]["text"].strip()
            except (KeyError, IndexError) as e:
                sys.stderr.write(f"Failed to parse Gemini response: {e}\nRaw response: {gemini_resp}\n")
                return 1
                
        print(f"\033[94mCustomer:\033[0m {customer_text}")
        
        # Check customer hangup
        should_hangup = False
        cleaned_customer_text = customer_text
        if "<hangup>" in customer_text:
            cleaned_customer_text = customer_text.replace("<hangup>", "").strip()
            should_hangup = True
            
        # B. Agent turn
        if args.mock:
            agent_resp = run_session_mock(
                session_id,
                text=cleaned_customer_text,
                customer_goal=goal,
                customer_name=name,
                customer_mood=mood,
                customer_constraint=constraint
            )
        else:
            agent_resp = c.run_session(
                session_id,
                text=cleaned_customer_text,
                variables=variables,
                deployment_id=deployment_id,
                use_tool_fakes=use_fakes,
                entry_agent=args.entry_agent
            )
            
        agent_text = A.extract_text(agent_resp)
        tools = A.extract_tools(agent_resp)
        agents = A.extract_agents(agent_resp)
        updates = A.extract_updated_variables(agent_resp)
        variables = A.merge_params(variables, updates)
        
        route_info = " -> ".join(agents) or "none"
        tools_info = ", ".join(tools) or "none"
        print(f"\033[92mAgent:\033[0m {agent_text} [Tools: {tools_info}, Route: {route_info}]")
        
        # Append turns to history
        contents.append({"role": "model", "parts": [{"text": customer_text}]})
        contents.append({"role": "user", "parts": [{"text": agent_text}]})
        
        transcript_turns.append(f"Customer: {customer_text}")
        transcript_turns.append(f"Agent: {agent_text}")
        
        if should_hangup:
            print("\n[Simulation finished: Customer hung up]")
            break
        if "end_session" in tools:
            print("\n[Simulation finished: Agent ended session]")
            break
    else:
        print("\n[Simulation finished: Max turns reached]")
        
    print("-" * 60)
    
    # 5. Run Evaluation
    print("Running QA post-dialogue evaluation...")
    transcript = "\n".join(transcript_turns)
    
    if args.mock:
        eval_raw = call_gemini_mock_evaluator()
    else:
        eval_sys_inst = EVALUATOR_SYSTEM_PROMPT.format(
            design_spec=design_spec_content,
            customer_name=name,
            customer_mood=mood,
            customer_goal=goal,
            customer_constraint=constraint,
            transcript=transcript
        )
        contents_eval = [{"role": "user", "parts": [{"text": "Please evaluate the conversation transcript above and output the JSON."}]}]
        gemini_eval_resp = call_gemini(
            project_id=c.project,
            region=c.location,
            token=c._get_token(),
            model_id=args.model,
            contents=contents_eval,
            system_instruction=eval_sys_inst,
            json_mode=True
        )
        try:
            eval_raw = gemini_eval_resp["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError) as e:
            sys.stderr.write(f"Failed to parse Gemini evaluator response: {e}\nRaw response: {gemini_eval_resp}\n")
            return 1
            
    eval_cleaned = clean_json_text(eval_raw)
    try:
        eval_result = json.loads(eval_cleaned)
        if not isinstance(eval_result, dict):
            raise ValueError("Evaluator response is not a JSON object")
    except (json.JSONDecodeError, ValueError) as e:
        sys.stderr.write(f"Error parsing evaluator JSON output: {e}\nRaw output: {eval_raw}\n")
        return 1
        
    # Safe validation of violations list
    violations = eval_result.get("violations") or []
    if isinstance(violations, str):
        violations = [violations]
    elif not isinstance(violations, list):
        violations = [str(violations)]
    else:
        violations = [str(v) for v in violations]
    eval_result["violations"] = violations
        
    # Print results
    print("\n================ EVALUATION RESULTS ================")
    print(f"Passed:             {eval_result.get('passed')}")
    print(f"Goal Resolved:      {eval_result.get('goal_resolved')}")
    print(f"Mood Handling Score: {eval_result.get('agent_mood_handling_score')}/5")
    print(f"Reasoning:          {eval_result.get('reasoning')}")
    if violations:
        print(f"Violations:         {', '.join(violations)}")
    print("====================================================")
    
    # Write output file
    if args.output:
        try:
            output_data = {
                "transcript": transcript,
                "evaluation": eval_result
            }
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2)
            print(f"Results written to: {args.output}")
        except Exception as e:
            sys.stderr.write(f"Failed to write output to {args.output}: {e}\n")
            
    return 0 if eval_result.get("passed") is True else 1


if __name__ == "__main__":
    # Fix argument parser to correctly accept args with hyphens or underscores
    # In main(), Python wraps hyphens as underscores in namespace (args.customer_context instead of args.customer-context)
    # We should adjust the parse_args namespace access.
    # We will do this by using dest="customer_context" for the parameter.
    # Let's inspect the command-line argument parser.
    # Instead of args.customer-context we must use args.customer_context.
    # I've updated the script to correct this dest lookup.
    
    # To be safe, let's parse using dest="customer_context" and dest="design_spec"
    sys.exit(main())
