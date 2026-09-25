// BCBS Minnesota Member Portal & CES Chatbot Frontend JavaScript

const SESSION_ID = 'bcbs_session_' + Math.random().toString(36).substring(2, 9);
let isBusinessHours = true;
let isWidgetOpen = false;

document.addEventListener('DOMContentLoaded', () => {
    // Setup Business Hours Toggle Listener
    const hoursToggle = document.getElementById('businessHoursToggle');
    const hoursStatusLabel = document.getElementById('hoursStatusLabel');

    if (hoursToggle) {
        hoursToggle.addEventListener('change', (e) => {
            isBusinessHours = e.target.checked;
            if (isBusinessHours) {
                hoursStatusLabel.textContent = "Open (8am - 8pm)";
                hoursStatusLabel.className = "status-open";
            } else {
                hoursStatusLabel.textContent = "Closed (Out-of-Hours)";
                hoursStatusLabel.className = "status-closed";
            }
        });
    }

    // Auto-open greeting on page load
    setTimeout(() => {
        if (!isWidgetOpen) {
            toggleChatWidget();
            sendUserMessage("Hello");
        }
    }, 1200);
});

function toggleChatWidget() {
    const windowEl = document.getElementById('chatWindow');
    isWidgetOpen = !isWidgetOpen;

    if (isWidgetOpen) {
        windowEl.classList.remove('hidden');
        document.getElementById('chatInput').focus();
    } else {
        windowEl.classList.add('hidden');
    }
}

function openChatWithPrompt(promptText) {
    if (!isWidgetOpen) {
        toggleChatWidget();
    }
    sendUserMessage(promptText);
}

function handleUserSubmit(e) {
    e.preventDefault();
    const inputEl = document.getElementById('chatInput');
    const text = inputEl.value.trim();
    if (text) {
        sendUserMessage(text);
        inputEl.value = '';
    }
}

function sendUserMessage(text) {
    const chatMessages = document.getElementById('chatMessages');

    // 1. Append User Bubble
    appendMessage(text, 'user');

    // 2. Show Typing Indicator
    showTypingIndicator();

    // 3. Clear Chips Area
    clearChips();

    // 4. POST to Backend API with fallback for static GitHub Pages hosting
    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: SESSION_ID,
            message: text,
            business_hours: isBusinessHours
        })
    })
    .then(res => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    })
    .then(data => handleChatResponse(data))
    .catch(err => {
        console.warn("Backend API endpoint /api/chat not reachable (Static GitHub Pages Mode). Generating client fallback response.");
        const fallbackData = generateClientFallbackResponse(text, isBusinessHours);
        setTimeout(() => handleChatResponse(fallbackData), 400);
    });
}

function handleChatResponse(data) {
    removeTypingIndicator();

    // If tool call, show badge
    if (data.tool_call) {
        appendToolBadge(`🛠️ Tool Executed: ${data.tool_call}`);
    }

    // Append Agent Response
    if (data.reply) {
        appendMessage(data.reply, 'agent');
    }

    // Render Quick Reply Chips
    if (data.chips && data.chips.length > 0) {
        renderChips(data.chips);
    }

    // If Transfer Triggered
    if (data.transfer) {
        setTimeout(() => {
            showTransferModal(data.transfer.reason, data.transfer.phone);
        }, 800);
    }
}

// Client-Side Conversational Engine for Static Deployment (GitHub Pages)
let clientState = {};
function generateClientFallbackResponse(text, hours) {
    const userLower = text.toLowerCase().strip ? text.toLowerCase().strip() : text.toLowerCase().trim();
    
    if (userLower.includes("emergency") || userLower.includes("chest pain") || userLower.includes("911") || userLower.includes("ambulance")) {
        return {
            reply: "If you have a medical emergency, please hang up and dial 911 immediately.",
            chips: ["Check Medicare Plans", "Rx Drug Coverage", "Speak to Advisor"],
            tool_call: null, transfer: null
        };
    }

    if (!hours) {
        return {
            reply: "Thank you for contacting Blue Cross/Blue Shield of Minnesota and Blue Plus. Our normal business hours are 8 am until 8 pm Monday through Friday. Please try again during normal business hours or schedule a callback.",
            chips: ["Schedule Callback", "Main Options"],
            tool_call: null, transfer: null
        };
    }

    if (userLower.includes("2026")) {
        return {
            reply: "If you have questions regarding 2026 coverage, I'll connect you with a representative who can assist you. One moment while I transfer your call.",
            chips: [],
            tool_call: "end_session",
            transfer: { reason: "2026 Coverage Inquiry", phone: "+1-800-555-0199" }
        };
    }

    if (userLower.includes("doctor appointment") || userLower.includes("dr appointment")) {
        return {
            reply: "Since you have a doctor appointment today, I am transferring you directly to Member Service. One moment please.",
            chips: [],
            tool_call: "end_session",
            transfer: { reason: "Doctor Appointment Priority", phone: "+1-800-555-0199" }
        };
    }

    if (userLower.includes("speak to agent") || userLower.includes("representative") || userLower.includes("human") || userLower.includes("advisor") || userLower.includes("talk to someone")) {
        return {
            reply: "I can certainly connect you with a Medicare Advisor! Can I please get your 5-digit zip code to find representative availability in your area?",
            chips: ["55401", "55101", "56001"],
            tool_call: null, transfer: null
        };
    }

    if (/\b\d{5}\b/.test(userLower)) {
        const zipMatch = userLower.match(/\b\d{5}\b/)[0];
        clientState.zip = zipMatch;
        if (zipMatch === "55401") {
            return {
                reply: `I found Medicare plan options available in **Hennepin County (ZIP ${zipMatch})**!\n\n• **Blue Cross Medicare Advantage Choice (PPO)** — $0 Monthly Premium, $0 Medical Deductible.\n• **Blue Cross Medicare Advantage Platinum (HMO)** — $45 Monthly Premium, Dental/Vision included.\n\nWould you like to check prescription drug coverage next?`,
                chips: ["Rx Drug Coverage", "Speak to Advisor", "Main Options"],
                tool_call: `lookup_plan_info(zip='${zipMatch}', county='Hennepin')`,
                transfer: null
            };
        } else if (zipMatch === "55101") {
            return {
                reply: `I found Medicare plan options available in **Ramsey County (ZIP ${zipMatch})**!\n\n• **Blue Cross Medicare Advantage Core (PPO)** — $0 Monthly Premium.\n• **Blue Cross Medicare Advantage Complete (HMO-POS)** — $25 Monthly Premium.\n\nWould you like to review Rx drug coverage?`,
                chips: ["Rx Drug Coverage", "Speak to Advisor", "Main Options"],
                tool_call: `lookup_plan_info(zip='${zipMatch}', county='Ramsey')`,
                transfer: null
            };
        } else if (zipMatch === "56001") {
            return {
                reply: `Zip code **56001** spans multiple counties (Blue Earth and Nicollet). Which county are you located in?`,
                chips: ["Blue Earth County", "Nicollet County"],
                tool_call: `lookup_zip_county(zip='56001')`,
                transfer: null
            };
        } else if (zipMatch === "55000") {
            return {
                reply: `I apologize, but we do not currently offer Medicare Advantage plans in zip code **55000**. Would you like me to connect you with a representative for Medicare Supplement options?`,
                chips: ["Speak to Advisor", "Main Options"],
                tool_call: `lookup_plan_info(zip='55000')`,
                transfer: null
            };
        } else {
            return {
                reply: `I found Medicare Advantage plans available for zip code **${zipMatch}** with $0 monthly premium options! Would you like to check prescription drug coverage?`,
                chips: ["Rx Drug Coverage", "Speak to Advisor"],
                tool_call: `lookup_plan_info(zip='${zipMatch}')`,
                transfer: null
            };
        }
    }

    if (userLower.includes("lipitor") || userLower.includes("metformin") || userLower.includes("lisinopril") || userLower.includes("atorvastatin") || userLower.includes("rx drug coverage") || userLower.includes("prescription") || userLower.includes("drug")) {
        if (userLower.includes("lipitor") || userLower.includes("atorvastatin")) {
            return {
                reply: "Good news! **Lipitor (Atorvastatin)** is covered under Tier 1 (Preferred Generic) with a **$0 copay** at preferred network pharmacies. Would you like to check another medication?",
                chips: ["Check Another Drug", "Main Options"],
                tool_call: "search_drug_formulary(drug='Lipitor')",
                transfer: null
            };
        } else if (userLower.includes("metformin") && userLower.includes("lisinopril")) {
            return {
                reply: "Both **Metformin** and **Lisinopril** are covered on our 2026 formulary under Tier 1 with **$0 copays**! Would you like to check any other drugs?",
                chips: ["Check Another Drug", "Main Options"],
                tool_call: "search_drug_formulary(drugs=['Metformin', 'Lisinopril'])",
                transfer: null
            };
        } else if (userLower.includes("nonexistent") || userLower.includes("xyz")) {
            return {
                reply: "I could not find **NonExistentDrugXYZ** in our standard formulary. I can check for generic equivalents or connect you with an Rx specialist.",
                chips: ["Speak to Advisor", "Main Options"],
                tool_call: null, transfer: null
            };
        } else {
            return {
                reply: "Please tell me the name of the prescription medication you would like to check on our 2026 formulary.",
                chips: ["Lipitor", "Metformin & Lisinopril", "Atorvastatin"],
                tool_call: null, transfer: null
            };
        }
    }

    if (userLower.includes("id card") || userLower.includes("claim") || userLower.includes("replace id")) {
        return {
            reply: "For existing member services, claims status, or replacing your ID card, please log into the Member Portal or call Member Service at **1-800-382-2000**.",
            chips: ["Check Plan Eligibility", "Rx Drug Coverage", "Main Options"],
            tool_call: null, transfer: null
        };
    }

    if (userLower.includes("recommend") || userLower.includes("which plan should i enroll") || userLower.includes("what plan is best")) {
        return {
            reply: "As an AI assistant, I cannot recommend a specific plan for you. However, I can explain plan features or connect you with a licensed Medicare Advisor to help you choose the best fit.",
            chips: ["Check Plan Eligibility", "Speak to Advisor"],
            tool_call: null, transfer: null
        };
    }

    if (userLower.includes("hello") || userLower.includes("hi") || userLower.includes("hey") || userLower.includes("start")) {
        return {
            reply: "Hello! Welcome to Blue Cross and Blue Shield of Minnesota. I can help you explore 2026 Medicare plan options, check zip code eligibility, or look up prescription drug coverage. How can I assist you today?",
            chips: ["Check Plan Eligibility", "Rx Drug Coverage", "Speak to Advisor"],
            tool_call: null, transfer: null
        };
    }

    if (userLower.includes("no") || userLower.includes("good") || userLower.includes("thanks") || userLower.includes("bye")) {
        return {
            reply: "Thank you for contacting Blue Cross and Blue Shield of Minnesota! Have a wonderful day.",
            chips: ["Start New Conversation"],
            tool_call: "end_session", transfer: null
        };
    }

    return {
        reply: "I am happy to assist you with Blue Cross/Blue Shield of Minnesota Medicare plans. You can check plan eligibility by entering your zip code or search our drug formulary.",
        chips: ["Check Plan Eligibility", "Rx Drug Coverage", "Speak to Advisor"],
        tool_call: null, transfer: null
    };
}

function appendMessage(text, sender) {
    const chatMessages = document.getElementById('chatMessages');
    const msgDiv = document.createElement('div');
    msgDiv.className = `msg ${sender}`;
    
    // Format bold text (**text**)
    let formattedText = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    msgDiv.innerHTML = formattedText;

    chatMessages.appendChild(msgDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendToolBadge(text) {
    const chatMessages = document.getElementById('chatMessages');
    const badgeDiv = document.createElement('div');
    badgeDiv.className = 'msg tool-badge';
    badgeDiv.textContent = text;
    chatMessages.appendChild(badgeDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTypingIndicator() {
    removeTypingIndicator();
    const chatMessages = document.getElementById('chatMessages');
    const indicator = document.createElement('div');
    indicator.id = 'typingIndicator';
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    chatMessages.appendChild(indicator);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeTypingIndicator() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
}

function renderChips(chips) {
    const chipsArea = document.getElementById('chatChipsArea');
    chipsArea.innerHTML = '';
    chips.forEach(chipText => {
        const btn = document.createElement('button');
        btn.className = 'chip-btn';
        btn.textContent = chipText;
        btn.onclick = () => sendUserMessage(chipText);
        chipsArea.appendChild(btn);
    });
}

function clearChips() {
    const chipsArea = document.getElementById('chatChipsArea');
    chipsArea.innerHTML = '';
}

function showTransferModal(reason, phone) {
    const modal = document.getElementById('transferModal');
    const reasonEl = document.getElementById('transferReason');
    if (reasonEl) reasonEl.textContent = reason;
    modal.classList.add('active');
}

function closeTransferModal() {
    const modal = document.getElementById('transferModal');
    modal.classList.remove('active');
}
