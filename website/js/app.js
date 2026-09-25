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

    // 4. POST to Backend API
    fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            session_id: SESSION_ID,
            message: text,
            business_hours: isBusinessHours
        })
    })
    .then(res => res.json())
    .then(data => {
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
    })
    .catch(err => {
        removeTypingIndicator();
        appendMessage("I'm sorry, I encountered a temporary connection issue. Please try again.", 'agent');
        console.error("Chat error:", err);
    });
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
