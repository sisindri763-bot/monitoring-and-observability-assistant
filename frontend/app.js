/* ==============================================================================
   Tusk Frontend Application Logic - Unified Dashboard & Chat Handler
   ============================================================================== */

const API_BASE = "http://127.0.0.1:8000"; // Point directly to the FastAPI backend server

// Initialize Mermaid.js
mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    securityLevel: 'loose',
    flowchart: { useMaxWidth: true, htmlLabels: true }
});

// App State
let conversationId = localStorage.getItem("tusk_conversation_id") || "";

// DOM Elements Cache
const healthRing = document.getElementById("health-ring");
const healthPct = document.getElementById("health-pct");
const healthState = document.getElementById("health-state");
const successRateVal = document.getElementById("success-rate-val");
const staleTablesVal = document.getElementById("stale-tables-val");
const volAnomaliesVal = document.getElementById("vol-anomalies-val");
const totalRunsVal = document.getElementById("total-runs-val");
const webhookList = document.getElementById("webhook-list");
const apiStatusDot = document.getElementById("api-status-dot");
const apiStatusText = document.getElementById("api-status-text");

const chatMessages = document.getElementById("chat-messages-container");
const chatInput = document.getElementById("chat-input-box");
const btnSend = document.getElementById("btn-send-message");
const btnClear = document.getElementById("btn-clear-chat");
const btnRefreshAlerts = document.getElementById("btn-refresh-alerts");
const suggestionChips = document.querySelectorAll(".suggestion-chip");

// Initialize
document.addEventListener("DOMContentLoaded", () => {
    // Refresh telemetry and icons
    fetchTelemetry();
    fetchAlertReceivers();
    lucide.createIcons();

    // Event Listeners
    btnSend.addEventListener("click", sendMessage);
    chatInput.addEventListener("keydown", handleTextareaKey);
    btnClear.addEventListener("click", clearConversation);
    btnRefreshAlerts.addEventListener("click", fetchAlertReceivers);

    // Suggestion chips handler
    suggestionChips.forEach(chip => {
        chip.addEventListener("click", () => {
            const queryText = chip.textContent.trim();
            chatInput.value = queryText;
            sendMessage();
        });
    });

    // Auto-focus chat input
    chatInput.focus();
});

// --- TELEMETRY MODULE ---

async function fetchTelemetry() {
    try {
        // Fetch dashboard summary
        const response = await fetch(`${API_BASE}/monitoring/dashboard/summary`);
        const result = await response.json();
        
        // If we get a response, the backend is definitely connected!
        setBackendConnected(true);

        if (result.success && result.data) {
            const data = result.data;
            
            // Calculate health metrics
            const totalRuns = parseInt(data.total_runs || 0);
            const failedRuns = parseInt(data.failed_runs || 0);
            const successRate = totalRuns > 0 ? ((totalRuns - failedRuns) / totalRuns) * 100 : 100.0;
            
            // Fetch stale tables & volume anomalies counts
            let staleCount = 0;
            try {
                const freshnessRes = await fetch(`${API_BASE}/freshness/status`);
                const freshnessData = await freshnessRes.json();
                staleCount = Array.isArray(freshnessData.data) 
                    ? freshnessData.data.filter(t => t.freshness_status === 'STALE').length 
                    : (freshnessData.data?.tables?.filter(t => t.freshness_status === 'STALE').length || 0);
            } catch (e) {
                console.error("Freshness status fetch failed", e);
            }

            let anomalyCount = 0;
            try {
                const volumeRes = await fetch(`${API_BASE}/volume/status`);
                const volumeData = await volumeRes.json();
                anomalyCount = Array.isArray(volumeData.data)
                    ? volumeData.data.filter(t => t.anomaly_status === 'ANOMALY').length
                    : (volumeData.data?.tables?.filter(t => t.anomaly_status === 'ANOMALY').length || 0);
            } catch (e) {
                console.error("Volume status fetch failed", e);
            }

            // Compute health score
            const healthScore = Math.round((successRate * 0.5) + 30 + (staleCount === 0 ? 10 : 0) + (anomalyCount === 0 ? 10 : 0));
            const boundedHealthScore = Math.min(100, Math.max(0, healthScore));

            updateDashboardUI(boundedHealthScore, successRate, staleCount, anomalyCount, totalRuns);
        } else {
            // DB might be offline or empty but server is running
            updateDashboardUI(0, 0, 0, 0, 0);
            healthState.textContent = "DB ISSUE";
        }
    } catch (err) {
        console.error("Telemetry fetch failed", err);
        setBackendConnected(false);
    }
}

function updateDashboardUI(healthScore, successRate, staleCount, anomalyCount, totalRuns) {
    // Update Ring percentage
    healthPct.textContent = `${healthScore}%`;
    
    // Circumference = 2 * Math.PI * r = 251.2
    const circumference = 251.2;
    const offset = circumference - (healthScore / 100) * circumference;
    healthRing.style.strokeDashoffset = offset;

    // Health state coloring
    if (healthScore >= 90) {
        healthRing.style.stroke = "var(--success)";
        healthState.className = "health-label success-theme";
        healthState.textContent = "HEALTHY";
    } else if (healthScore >= 70) {
        healthRing.style.stroke = "var(--warning)";
        healthState.className = "health-label alert-theme";
        healthState.textContent = "WARNING";
    } else {
        healthRing.style.stroke = "var(--error)";
        healthState.className = "health-label error-theme";
        healthState.textContent = "CRITICAL";
    }

    // Telemetry values
    successRateVal.textContent = `${successRate.toFixed(1)}%`;
    staleTablesVal.textContent = staleCount;
    volAnomaliesVal.textContent = anomalyCount;
    totalRunsVal.textContent = totalRuns;
}

async function fetchAlertReceivers() {
    try {
        const response = await fetch(`${API_BASE}/alerts`);
        const result = await response.json();
        
        webhookList.innerHTML = "";
        
        const receivers = result.data?.webhooks || result.data || [];
        if (Array.isArray(receivers) && receivers.length > 0) {
            receivers.forEach(item => {
                const urlObj = new URL(item.url);
                const hostname = urlObj.hostname;
                const pathEnd = urlObj.pathname.substring(urlObj.pathname.lastIndexOf('/') + 1);
                const displayUrl = `${hostname}/.../${pathEnd}`;

                const row = document.createElement("div");
                row.className = "alert-receiver-item animate-fade-in";
                row.innerHTML = `
                    <div class="alert-receiver-info">
                        <span class="alert-receiver-name" title="${item.url}">${displayUrl}</span>
                        <span class="alert-receiver-type">ID ${item.webhook_id} • Scope: ${item.event_type}</span>
                    </div>
                    <button class="btn btn-secondary btn-icon-only text-red-500" onclick="deleteWebhook(${item.webhook_id})" title="Delete webhook">
                        <i data-lucide="trash-2" style="width: 14px; height: 14px; color: var(--error);"></i>
                    </button>
                `;
                webhookList.appendChild(row);
            });
            lucide.createIcons();
        } else {
            webhookList.innerHTML = `<div class="empty-state">No webhooks registered</div>`;
        }
    } catch (err) {
        webhookList.innerHTML = `<div class="empty-state" style="color: var(--error)">Failed to retrieve webhooks</div>`;
    }
}

async function deleteWebhook(id) {
    if (!confirm(`Are you sure you want to remove webhook receiver ID ${id}?`)) return;
    try {
        const response = await fetch(`${API_BASE}/alerts/${id}`, { method: "DELETE" });
        const result = await response.json();
        if (result.success) {
            fetchAlertReceivers();
            // Automatically add an assistant notification in chat
            appendSystemMessage(`Alert Webhook receiver ID ${id} was deleted successfully.`);
        }
    } catch (err) {
        alert("Failed to delete webhook receiver");
    }
}

function setBackendConnected(isConnected) {
    if (isConnected) {
        apiStatusDot.className = "pulse-indicator healthy";
        apiStatusText.textContent = "Backend Connected";
    } else {
        apiStatusDot.className = "pulse-indicator unhealthy";
        apiStatusText.textContent = "Offline / Connection Error";
        healthState.textContent = "OFFLINE";
        healthRing.style.strokeDashoffset = 251.2;
    }
}

// --- CHAT ENGINE MODULE ---

function handleTextareaKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    // Clear input
    chatInput.value = "";
    chatInput.style.height = "auto";

    // Append User message to container
    appendMessage(text, "user");

    // Add Typing indicator
    const typingIndicator = appendTypingIndicator();

    try {
        // Post request to copilot agent API
        const response = await fetch(`${API_BASE}/agents/copilot`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: jsonPayload(text, conversationId)
        });

        const result = await response.json();
        removeTypingIndicator(typingIndicator);

        if (result.success) {
            // Save conversation ID session key
            if (!conversationId && result.conversation_id) {
                conversationId = result.conversation_id;
                localStorage.setItem("tusk_conversation_id", conversationId);
            }
            
            // Append assistant response to chat
            appendMessage(result.message, "assistant");
            
            // Refresh telemetry sidebar metrics if agents made database updates
            fetchTelemetry();
            fetchAlertReceivers();
        } else {
            appendMessage(`Error: ${result.message || 'Tusk encountered a server run error.'}`, "assistant");
        }
    } catch (err) {
        removeTypingIndicator(typingIndicator);
        appendMessage("Connection failed. Please ensure the FastAPI backend server is online and try again.", "assistant");
    }
}

function appendMessage(text, sender) {
    const isAssistant = sender === "assistant";
    const msgBox = document.createElement("div");
    msgBox.className = `message ${sender}-message animate-fade-in`;
    
    const avatar = isAssistant ? "bot" : "user";
    
    // Parse formatting natively
    const htmlContent = isAssistant ? formatMarkdown(text) : escapeHtml(text);

    msgBox.innerHTML = `
        <div class="message-avatar"><i data-lucide="${avatar}"></i></div>
        <div class="message-content">${htmlContent}</div>
    `;

    chatMessages.appendChild(msgBox);
    lucide.createIcons();

    // Render Mermaid diagrams inside the newly appended block
    if (isAssistant) {
        try {
            mermaid.run({
                nodes: msgBox.querySelectorAll('.mermaid')
            });
        } catch (e) {
            console.error("Mermaid compilation error", e);
        }
    }

    // Scroll chat list to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendSystemMessage(text) {
    const msgBox = document.createElement("div");
    msgBox.className = "message assistant-message animate-fade-in";
    msgBox.innerHTML = `
        <div class="message-avatar"><i data-lucide="bot"></i></div>
        <div class="message-content"><p><em>${escapeHtml(text)}</em></p></div>
    `;
    chatMessages.appendChild(msgBox);
    lucide.createIcons();
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function appendTypingIndicator() {
    const msgBox = document.createElement("div");
    msgBox.className = "message assistant-message animate-fade-in";
    msgBox.innerHTML = `
        <div class="message-avatar"><i data-lucide="bot"></i></div>
        <div class="message-content">
            <div class="loading-dots">
                <div class="dot"></div>
                <div class="dot"></div>
                <div class="dot"></div>
            </div>
        </div>
    `;
    chatMessages.appendChild(msgBox);
    lucide.createIcons();
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return msgBox;
}

function removeTypingIndicator(indicatorElement) {
    if (indicatorElement && indicatorElement.parentNode) {
        indicatorElement.parentNode.removeChild(indicatorElement);
    }
}

function clearConversation() {
    if (confirm("Are you sure you want to clear chat history? This resets thread context session memory.")) {
        conversationId = "";
        localStorage.removeItem("tusk_conversation_id");
        chatMessages.innerHTML = `
            <div class="message assistant-message animate-fade-in">
                <div class="message-avatar"><i data-lucide="bot"></i></div>
                <div class="message-content">
                    <p>Thread context reset successfully. Ask me anything to start a new chat session!</p>
                </div>
            </div>
        `;
        lucide.createIcons();
    }
}

// --- UTILITIES / PARSERS ---

function jsonPayload(message, convoId) {
    return JSON.stringify({
        message: message,
        conversation_id: convoId || null
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Client-side markdown + mermaid formatter
function formatMarkdown(text) {
    let html = text;

    // 1. Render block code & Mermaid diagrams
    const codeBlockRegex = /```(mermaid|sql|bash|json|python)?\s*([\s\S]*?)```/g;
    html = html.replace(codeBlockRegex, (match, lang, code) => {
        code = code.trim();
        if (lang === "mermaid") {
            return `<div class="mermaid">${code}</div>`;
        }
        return `<pre><code class="language-${lang || 'txt'}">${escapeHtml(code)}</code></pre>`;
    });

    // Escape basic html tags outside pre/code wrappers by splitting
    const parts = html.split(/(<pre[\s\S]*?<\/pre>|<div class="mermaid">[\s\S]*?<\/div>)/);
    for (let i = 0; i < parts.length; i++) {
        if (!parts[i].startsWith('<pre') && !parts[i].startsWith('<div')) {
            let chunk = parts[i];
            
            // Headers
            chunk = chunk.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
            chunk = chunk.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
            chunk = chunk.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
            
            // Bold & Italics
            chunk = chunk.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            chunk = chunk.replace(/\*(.*?)\*/g, '<em>$1</em>');
            
            // Inline code
            chunk = chunk.replace(/`(.*?)`/g, '<code>$1</code>');
            
            // Unordered list items
            chunk = chunk.replace(/^\*\s+(.*?)$/gm, '<li>$1</li>');
            chunk = chunk.replace(/^-\s+(.*?)$/gm, '<li>$1</li>');
            
            // Ordered list items
            chunk = chunk.replace(/^\d+\.\s+(.*?)$/gm, '<li>$1</li>');
            
            // Wrap sets of <li> inside lists
            chunk = chunk.replace(/(<li>.*?<\/li>)+/gs, (listMatch) => `<ul>${listMatch}</ul>`);
            
            // Paragraph breaks (double newlines)
            chunk = chunk.replace(/\n\n/g, '</p><p>');
            chunk = chunk.replace(/\n/g, '<br>');
            
            parts[i] = chunk;
        }
    }

    html = parts.join('');
    
    // Ensure wraps in paragraph tags if not structured
    if (!html.startsWith('<h') && !html.startsWith('<p') && !html.startsWith('<pre') && !html.startsWith('<ul')) {
        html = `<p>${html}</p>`;
    }
    
    return html;
}
