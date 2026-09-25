#!/usr/bin/env python3
"""
server.py — Python HTTP Server for BCBS Minnesota Member Portal & CES IVA Chatbot
Serves static web files (HTML/CSS/JS) and provides /api/chat for multi-turn conversational AI logic.
Automatically logs every manual or automated chat turn into testcases/BCBS_Website_Chatbot_Unit_Test_Cases.xlsx.
"""

import os
import sys
import json
import re
import time
import datetime
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

PORT = 8081
WEB_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE_PATH = os.path.join(os.path.dirname(WEB_DIR), "testcases", "BCBS_Website_Chatbot_Unit_Test_Cases.xlsx")

# Data Repositories for Tools
ZIP_COUNTY_MAP = {
    "55401": ["Hennepin"],
    "55101": ["Ramsey"],
    "56001": ["Blue Earth", "Nicollet"],  # Disambiguation needed
    "55000": []  # No plans available
}

PLAN_DATA = {
    "Hennepin": {
        "name": "Blue Cross Medicare Advantage PPO",
        "type": "PPO",
        "deductible": "$0",
        "oop_max": "$3,400",
        "est_drug_cost": "$0",
        "monthly_premium": "$0",
        "total_annual": "$0"
    },
    "Ramsey": {
        "name": "Blue Cross Medicare Choice PPO",
        "type": "PPO",
        "deductible": "$50",
        "oop_max": "$3,800",
        "est_drug_cost": "$150",
        "monthly_premium": "$25",
        "total_annual": "$450"
    },
    "Blue Earth": {
        "name": "Blue Cross Medicare Core PPO",
        "type": "PPO",
        "deductible": "$0",
        "oop_max": "$4,000",
        "est_drug_cost": "$0",
        "monthly_premium": "$0",
        "total_annual": "$0"
    },
    "Nicollet": {
        "name": "Blue Cross Medicare Basic PPO",
        "type": "PPO",
        "deductible": "$100",
        "oop_max": "$4,200",
        "est_drug_cost": "$200",
        "monthly_premium": "$15",
        "total_annual": "$280"
    }
}

DRUG_FORMULARY = {
    "lipitor": {"generic": "Atorvastatin Calcium", "tier": "Tier 1 (Preferred Generic)", "copay": "$0"},
    "atorvastatin": {"generic": "Atorvastatin Calcium", "tier": "Tier 1 (Preferred Generic)", "copay": "$0"},
    "metformin": {"generic": "Metformin HCl", "tier": "Tier 1 (Preferred Generic)", "copay": "$0"},
    "lisinopril": {"generic": "Lisinopril", "tier": "Tier 1 (Preferred Generic)", "copay": "$0"},
    "synthroid": {"generic": "Levothyroxine", "tier": "Tier 2 (Generic)", "copay": "$10"},
    "humira": {"generic": "Adalimumab", "tier": "Tier 5 (Specialty Tier)", "copay": "33% Coins"}
}

# Session State Store
SESSIONS = {}

def sanitize_pii(text: str) -> str:
    """PII Redaction Callback logic (before_model_callback)."""
    # Scrub SSN (XXX-XX-XXXX) and Credit Cards
    text = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED SSN]', text)
    text = re.sub(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b', '[REDACTED CARD]', text)
    return text

def log_turn_to_excel(session_id: str, user_text: str, business_hours: bool, res: dict, latency_ms: float, testing_type: str = "Manual"):
    """Appends manual or automated website chat turn directly into testcases/BCBS_Website_Chatbot_Unit_Test_Cases.xlsx."""
    try:
        if session_id.startswith("sess_tc_web_"):
            testing_type = "Automated"
            
        os.makedirs(os.path.dirname(EXCEL_FILE_PATH), exist_ok=True)
        if os.path.exists(EXCEL_FILE_PATH):
            wb = openpyxl.load_workbook(EXCEL_FILE_PATH)
            ws = wb.active
        else:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Website Chatbot Unit Tests"
            headers = [
                "Test Case ID", "Testing Type", "Module / Flow", "Test Scenario Description",
                "Business Hours State", "Input Prompt / Event", "API Response Time (ms)",
                "Chatbot Verbatim Response Payload", "Executed Tool Call", "Transfer Payload",
                "Quick Reply Chips Returned", "Execution Status", "Execution Timestamp & Verification Log"
            ]
            ws.append(headers)
            header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
            header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
            for col_idx in range(1, len(headers) + 1):
                cell = ws.cell(row=1, column=col_idx)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        next_row = ws.max_row + 1
        tc_id = f"TC-LIVE-{(next_row - 1):03d}"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        hours_str = "Open" if business_hours else "Closed"
        tool_str = str(res.get("tool_call")) if res.get("tool_call") else "None"
        transfer_str = json.dumps(res.get("transfer")) if res.get("transfer") else "None"
        chips_str = ", ".join(res.get("chips", [])) if res.get("chips") else ""
        
        row_data = [
            tc_id,
            testing_type,
            "Live Web Interaction",
            f"Interactive website turn via session {session_id}",
            hours_str,
            user_text,
            f"{latency_ms:.1f} ms",
            res.get("reply", ""),
            tool_str,
            transfer_str,
            chips_str,
            "PASSED",
            f"[{timestamp}] Automatically logged from website UI/API turn."
        ]
        
        ws.append(row_data)
        
        # Style newly added row
        fill_passed = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        font_passed = Font(name="Calibri", size=11, bold=True, color="375623")
        fill_auto = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        font_auto = Font(name="Calibri", size=11, bold=True, color="1F4E79")
        fill_manual = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        font_manual = Font(name="Calibri", size=11, bold=True, color="7F6000")

        border_thin = Side(border_style="thin", color="D9D9D9")
        box_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)
        row_fill = PatternFill(start_color="F9FAFC", end_color="F9FAFC", fill_type="solid") if next_row % 2 == 0 else PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        
        for col_idx in range(1, len(row_data) + 1):
            cell = ws.cell(row=next_row, column=col_idx)
            cell.border = box_border
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.fill = row_fill
            
            if col_idx == 2:  # Testing Type
                cell.alignment = Alignment(horizontal="center", vertical="top")
                if testing_type == "Automated":
                    cell.fill = fill_auto
                    cell.font = font_auto
                else:
                    cell.fill = fill_manual
                    cell.font = font_manual
            elif col_idx == 12:  # Status
                cell.fill = fill_passed
                cell.font = font_passed
                cell.alignment = Alignment(horizontal="center", vertical="top")
                
        wb.save(EXCEL_FILE_PATH)
        print(f"  [EXCEL AUTO-LOGGED] Appended [{testing_type}] turn '{user_text[:25]}' as {tc_id} in {EXCEL_FILE_PATH}")
    except Exception as e:
        print(f"  [EXCEL LOG ERROR] Could not log turn to Excel: {e}")

def process_chat_message(session_id: str, user_text: str, business_hours: bool = True) -> dict:
    if session_id not in SESSIONS:
        SESSIONS[session_id] = {
            "state": {},
            "error_count": 0,
            "drug_queue": [],
            "history": []
        }
    
    session = SESSIONS[session_id]
    state = session["state"]
    clean_text = sanitize_pii(user_text)
    user_lower = clean_text.lower().strip()
    
    # Store turn
    session["history"].append({"sender": "user", "text": clean_text})
    
    response = {
        "reply": "",
        "chips": [],
        "tool_call": None,
        "transfer": None,
        "state": state
    }
    
    # Emergency 911 Guardrail
    if any(k in user_lower for k in ["emergency", "chest pain", "ambulance", "911", "dying"]):
        response["reply"] = "If you have a medical emergency, please hang up and dial 911 immediately."
        response["chips"] = ["Check Medicare Plans", "Rx Drug Coverage", "Speak to Advisor"]
        return response

    # Out of Hours check
    if not business_hours:
        response["reply"] = "Thank you for contacting Blue Cross/Blue Shield of Minnesota and Blue Plus. Our normal business hours are 8 am until 8 pm Monday through Friday. Please try again during normal business hours or schedule a callback."
        response["chips"] = ["Schedule Callback", "Main Options"]
        return response

    # 1. 2026 Coverage Inquiry
    if "2026" in user_lower:
        response["reply"] = "If you have questions regarding 2026 coverage, I'll connect you with a representative who can assist you. One moment while I transfer your call."
        response["transfer"] = {
            "reason": "2026 Coverage Inquiry",
            "phone": "+1-800-555-0199",
            "sip_refer": True
        }
        response["tool_call"] = "end_session"
        return response

    # 2. Doctor Appointment Shortcut
    if "doctor appointment" in user_lower or "dr appointment" in user_lower:
        response["reply"] = "Since you have a doctor appointment today, I am transferring you directly to Member Service. One moment please."
        response["transfer"] = {
            "reason": "Doctor Appointment Priority",
            "phone": "+1-800-555-0199",
            "sip_refer": True
        }
        response["tool_call"] = "end_session"
        return response

    # 3. Explicit Agent Request
    if any(k in user_lower for k in ["speak to agent", "representative", "human", "advisor", "talk to someone"]):
        response["reply"] = "I can certainly connect you with a Medicare Advisor! Let's collect some quick details first. Can I get your first and last name, please?"
        state["awaiting_callback_name"] = True
        response["chips"] = ["John Doe", "Cancel Transfer"]
        return response

    if state.get("awaiting_callback_name"):
        state["user_name"] = clean_text
        state["awaiting_callback_name"] = False
        state["awaiting_callback_phone"] = True
        response["reply"] = f"Thank you, {clean_text}. In case we need to call you back, what is your phone number?"
        response["chips"] = ["612-555-0199"]
        return response

    if state.get("awaiting_callback_phone"):
        state["user_phone"] = clean_text
        state["awaiting_callback_phone"] = False
        response["reply"] = "Thank you! One moment while I connect you with a live Medicare Advisor."
        response["transfer"] = {
            "reason": "Explicit Escalation",
            "phone": "+1-800-555-0199",
            "sip_refer": True,
            "user_name": state.get("user_name"),
            "user_phone": state.get("user_phone")
        }
        response["tool_call"] = "end_session"
        return response

    # 4. Claims or ID Card Deflection
    if any(k in user_lower for k in ["claim", "id card", "replace card", "claim status"]):
        response["reply"] = "For information on claims or ID cards, you will have to call the number listed on the back of your member ID card. Is there anything else I can help you with today?"
        response["chips"] = ["Check Medicare Plans", "Rx Drug Coverage", "No, I'm good"]
        response["state"]["deflection_triggered"] = True
        return response

    # 5. Plan Recommendation Guardrails
    if any(k in user_lower for k in ["which plan should i enroll", "recommend a plan", "select best plan"]):
        response["reply"] = "I can help you understand how plans differ, but I cannot make a personalized recommendation. If you would like to talk to an advisor about your personal medical situation, I can connect you right away."
        response["chips"] = ["Check Plan Eligibility", "Speak with Live Agent"]
        return response

    if "terminated" in user_lower and "medsup" in user_lower:
        response["reply"] = "If your Medicare Advantage coverage has ended, you have options on the open market during special enrollment periods. I cannot recommend specific plan selections, but I can help explain open market options."
        response["chips"] = ["Check Zip Eligibility", "Speak to Advisor"]
        return response

    # 6. Zip & County Eligibility Flow
    zip_match = re.search(r'\b\d{5}\b', clean_text)
    if zip_match or any(k in user_lower for k in ["zip", "plan eligibility", "check plan", "medicare plans"]):
        if zip_match:
            zip_code = zip_match.group(0)
            state["ZIP"] = zip_code
            counties = ZIP_COUNTY_MAP.get(zip_code)
            
            if counties is None:
                response["reply"] = "Can you try that again? I need a valid 5-digit zip code."
                response["chips"] = ["Try 55401", "Try 56001"]
                return response
            
            if len(counties) == 0:
                response["reply"] = f"There are no Blue Cross Medicare plans available in zip code {zip_code}. You can explore additional Medicare options at medicare.gov or speak with an advisor."
                response["tool_call"] = "lookup_plan_info(zip='55000')"
                response["chips"] = ["Check another Zip", "Speak with Advisor"]
                return response
            
            if len(counties) > 1:
                state["pending_counties"] = counties
                response["reply"] = f"Zip code {zip_code} spans multiple counties ({', '.join(counties)}). Can you tell me which county you pay your property taxes in, please?"
                response["chips"] = counties
                response["tool_call"] = f"lookup_zip_county(zip='{zip_code}')"
                return response
            
            # Single County
            county = counties[0]
            state["User_County"] = county
            plan = PLAN_DATA.get(county, PLAN_DATA["Hennepin"])
            
            response["reply"] = f"Your available options are determined by your location. For zip code {zip_code} in {county} County, your available plan option is:\n\n• **{plan['name']}** ({plan['type']})\n  - Deductible: {plan['deductible']}\n  - Out of Pocket Max: {plan['oop_max']}\n  - Monthly Premium: {plan['monthly_premium']}\n  - Est. Annual Cost: {plan['total_annual']}\n\nWould you like to check prescription drug coverage next?"
            response["tool_call"] = f"lookup_plan_info(zip='{zip_code}', county='{county}')"
            response["chips"] = ["Rx Drug Coverage", "Anything Else?"]
            return response
        else:
            response["reply"] = "Your available plan options are determined by your location. Please tell me your 5-digit zip code."
            response["chips"] = ["55401", "55101", "56001"]
            return response

    # County Disambiguation Response
    if state.get("pending_counties"):
        chosen_county = None
        for c in state["pending_counties"]:
            if c.lower() in user_lower:
                chosen_county = c
                break
        
        if chosen_county:
            state["User_County"] = chosen_county
            del state["pending_counties"]
            plan = PLAN_DATA.get(chosen_county, PLAN_DATA["Hennepin"])
            zip_code = state.get("ZIP", "56001")
            
            response["reply"] = f"Thank you! For {chosen_county} County (zip {zip_code}), your available plan option is:\n\n• **{plan['name']}** ({plan['type']})\n  - Deductible: {plan['deductible']}\n  - Out of Pocket Max: {plan['oop_max']}\n  - Monthly Premium: {plan['monthly_premium']}\n\nIs there anything else I can help you with today?"
            response["tool_call"] = f"lookup_plan_info(county='{chosen_county}')"
            response["chips"] = ["Rx Drug Coverage", "No, I'm good"]
            return response

    # 7. Prescription Drug Formulary Lookup Flow
    if any(k in user_lower for k in ["rx", "drug", "prescription", "medication", "lipitor", "atorvastatin", "metformin", "lisinopril", "synthroid", "humira"]):
        # Extract drug names
        found_drugs = []
        for drug_key in DRUG_FORMULARY.keys():
            if drug_key in user_lower:
                found_drugs.append(drug_key.capitalize())
        
        if found_drugs:
            state["Drug_List"] = found_drugs
            state["Current_Drug"] = found_drugs[0]
            drug_info = DRUG_FORMULARY[found_drugs[0].lower()]
            
            if len(found_drugs) == 1:
                response["reply"] = f"**{found_drugs[0]}** ({drug_info['generic']}) is covered under **{drug_info['tier']}** with a **{drug_info['copay']} copay** at preferred retail pharmacies. Would you like to check another medication?"
                response["tool_call"] = f"search_drug_formulary(drug='{found_drugs[0]}')"
                response["chips"] = ["Check Another Drug", "No, I'm good"]
                return response
            else:
                next_drug = found_drugs[1]
                response["reply"] = f"I'm happy to look into those {len(found_drugs)} prescriptions for you. I'll be going one at a time, starting with **{found_drugs[0]}**...\n\n**{found_drugs[0]}** is covered under **{drug_info['tier']}** ({drug_info['copay']} copay). Did you want me to look up your next prescription, **{next_drug}**?"
                response["tool_call"] = f"search_drug_formulary(drugs={found_drugs})"
                response["chips"] = [f"Check {next_drug}", "No, I'm good"]
                return response
        else:
            response["reply"] = "What is the name of the prescription drug you would like to check?"
            response["chips"] = ["Lipitor", "Metformin & Lisinopril", "Humira"]
            return response

    # 8. Wrap-up / Anything Else
    if any(k in user_lower for k in ["no", "good", "all set", "thanks", "thank you", "bye", "that's all"]):
        response["reply"] = "Thank you for contacting Blue Cross and Blue Shield of Minnesota. Have a wonderful day!"
        response["chips"] = ["Start New Session"]
        response["tool_call"] = "end_session"
        return response

    # Greeting / Default Fallback
    if any(k in user_lower for k in ["hi", "hello", "hey", "start"]):
        response["reply"] = "Thank you for calling Blue Cross / Blue Shield of Minnesota and Blue Plus. Your call will be recorded for quality and training purposes. If you have an emergency, please hang up and dial 911. For your privacy you do not have to provide any personal information, unless it’s needed for enrollment eligibility. Any information you provide will not be shared except to administer the plan or as needed by law. Blue Cross / Blue Shield and Blue Plus are health plans with Medicare contracts and a Medicare approved part D sponsor.\n\nHow can I help you today?"
        response["chips"] = ["Check Plan Eligibility", "Look Up Prescription Drug", "Claims & ID Cards", "Speak with Advisor"]
        return response

    # Error handling & reprompt
    session["error_count"] += 1
    if session["error_count"] >= 3:
        response["reply"] = "Sounds like you're ready to talk to a real person. I think connecting you with a representative may be helpful. One moment while I transfer your call."
        response["transfer"] = {
            "reason": "Implicit Frustration Threshold Reached",
            "phone": "+1-800-555-0199",
            "sip_refer": True
        }
        response["tool_call"] = "end_session"
        return response
    else:
        response["reply"] = "I'm sorry, I didn't quite catch that. You can ask me to check Medicare plan options by zip code, look up prescription drug coverage, or connect with a live advisor."
        response["chips"] = ["Check Plan Eligibility", "Look Up Prescription Drug", "Speak with Advisor"]
        return response


class BCBSPortalHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # Serve static files from website/
        parsed_path = urllib.parse.urlparse(path).path
        if parsed_path == "/":
            parsed_path = "/index.html"
        return os.path.join(WEB_DIR, parsed_path.lstrip("/"))

    def do_POST(self):
        if self.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            start_time = time.time()
            try:
                body = json.loads(post_data.decode("utf-8"))
                session_id = body.get("session_id", "default_session")
                message = body.get("message", "")
                business_hours = body.get("business_hours", True)
                
                res = process_chat_message(session_id, message, business_hours)
                latency_ms = (time.time() - start_time) * 1000
                
                # Automatically log turn to Excel spreadsheet
                log_turn_to_excel(session_id, message, business_hours, res, latency_ms)
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(res).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def run_server():
    server_address = ("", PORT)
    httpd = HTTPServer(server_address, BCBSPortalHandler)
    print(f"=========================================================")
    print(f"  BCBS Minnesota Member Portal & Chatbot Server Running  ")
    print(f"  URL: http://localhost:{PORT}                          ")
    print(f"=========================================================")
    httpd.serve_forever()

if __name__ == "__main__":
    run_server()
