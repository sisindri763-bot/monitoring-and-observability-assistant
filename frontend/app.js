/* ==============================================================================
   Tusk Frontend SPA Client Logic - Multi-Tab Observability Platform
   ============================================================================== */

const API_BASE = "http://127.0.0.1:8000"; // Connect to FastAPI backend CORS host

// Initialize Mermaid.js
mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    securityLevel: 'loose',
    flowchart: { useMaxWidth: true, htmlLabels: true }
});

// App State
let conversationId = localStorage.getItem("tusk_conversation_id") || "";
let activeTab = "tab-overview";

// DOM Elements Cache
const navItems = document.querySelectorAll(".nav-item");
const tabPanes = document.querySelectorAll(".tab-pane");

const apiStatusDot = document.getElementById("api-status-dot");
const apiStatusText = document.getElementById("api-status-text");

// Overview Elements
const successRateVal = document.getElementById("success-rate-val");
const staleTablesVal = document.getElementById("stale-tables-val");
const volAnomaliesVal = document.getElementById("vol-anomalies-val");
const totalRunsVal = document.getElementById("total-runs-val");

const donutPct = document.getElementById("donut-pct");
const donutSuccess = document.getElementById("donut-success");
const donutFailed = document.getElementById("donut-failed");
const donutSuccessCnt = document.getElementById("donut-success-cnt");
const donutFailedCnt = document.getElementById("donut-failed-cnt");

const webhookList = document.getElementById("webhook-list");
const btnRefreshOverview = document.getElementById("btn-refresh-overview");
const btnRefreshAlerts = document.getElementById("btn-refresh-alerts");

// Pipelines Elements
const pipelineSnapshots = document.getElementById("pipeline-snapshots");
const btnRefreshPipelines = document.getElementById("btn-refresh-pipelines");
const btnLoadLineage = document.getElementById("btn-load-lineage");
const lineagePlaceholder = document.getElementById("lineage-placeholder");
const lineageMermaidFlow = document.getElementById("lineage-mermaid-flow");

// Chat Elements
const chatMessages = document.getElementById("chat-messages-container");
const chatInput = document.getElementById("chat-input-box");
const btnSend = document.getElementById("btn-send-message");
const btnClear = document.getElementById("btn-clear-chat");
const suggestionChips = document.querySelectorAll(".suggestion-chip");

// --- INITIALIZE & ROUTING ---

document.addEventListener("DOMContentLoaded", () => {
    // Navigation Toggles
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const targetTab = item.getAttribute("data-tab");
            switchTab(targetTab);
        });
    });

    // Event Listeners
    btnSend.addEventListener("click", sendMessage);
    chatInput.addEventListener("keydown", handleTextareaKey);
    btnClear.addEventListener("click", clearConversation);
    btnRefreshOverview.addEventListener("click", fetchTelemetry);
    btnRefreshAlerts.addEventListener("click", fetchAlertReceivers);
    btnRefreshPipelines.addEventListener("click", fetchPipelineSnapshots);
    btnLoadLineage.addEventListener("click", renderLineageFlow);

    // Suggestion chips helper
    suggestionChips.forEach(chip => {
        chip.addEventListener("click", () => {
            const queryText = chip.textContent.trim();
            // Automatically switch to Chat tab
            switchTab("tab-copilot");
            chatInput.value = queryText;
            sendMessage();
        });
    });

    // Load Initial Data
    fetchTelemetry();
    fetchAlertReceivers();
    fetchPipelineSnapshots();
    lucide.createIcons();
});

function switchTab(tabId) {
    activeTab = tabId;
    
    // Update nav active states
    navItems.forEach(item => {
        if (item.getAttribute("data-tab") === tabId) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });

    // Update tab pane visibility
    tabPanes.forEach(pane => {
        if (pane.id === tabId) {
            pane.classList.add("active");
        } else {
            pane.classList.remove("active");
        }
    });

    // Auto-focus chat input if Copilot tab selected
    if (tabId === "tab-copilot") {
        chatInput.focus();
    }
}

// --- TELEMETRY MODULE & CHARTS ---

async function fetchTelemetry() {
    try {
        const response = await fetch(`${API_BASE}/monitoring/dashboard/summary`);
        const result = await response.json();
        
        setBackendConnected(true);

        if (result.success && result.data) {
            const data = result.data;
            const totalRuns = parseInt(data.total_executions || 0);
            const failedRuns = parseInt(data.failed_count || 0);
            const successRuns = parseInt(data.success_count || 0);
            const successRate = totalRuns > 0 ? (successRuns / totalRuns) * 100 : 0.0;
            
            // Stale tables count
            let staleCount = 0;
            try {
                const freshnessRes = await fetch(`${API_BASE}/freshness/status`);
                const freshnessData = await freshnessRes.json();
                staleCount = Array.isArray(freshnessData.data) 
                    ? freshnessData.data.filter(t => t.freshness_status === 'STALE').length 
                    : (freshnessData.data?.tables?.filter(t => t.freshness_status === 'STALE').length || 0);
            } catch (e) {
                console.error("Freshness fetch failed", e);
            }

            // Anomalies count
            let anomalyCount = 0;
            try {
                const volumeRes = await fetch(`${API_BASE}/volume/status`);
                const volumeData = await volumeRes.json();
                anomalyCount = Array.isArray(volumeData.data)
                    ? volumeData.data.filter(t => t.anomaly_status === 'ANOMALY').length
                    : (volumeData.data?.tables?.filter(t => t.anomaly_status === 'ANOMALY').length || 0);
            } catch (e) {
                console.error("Volume fetch failed", e);
            }

            // Update UI widgets
            successRateVal.textContent = `${successRate.toFixed(1)}%`;
            staleTablesVal.textContent = staleCount;
            volAnomaliesVal.textContent = anomalyCount;
            totalRunsVal.textContent = totalRuns;

            // Render Donut Chart
            updateDonutChart(successRate, successRuns, failedRuns);
        }
    } catch (err) {
        console.error("Failed to fetch telemetry overview", err);
        setBackendConnected(false);
    }
}

function updateDonutChart(successRate, successRuns, failedRuns) {
    donutPct.textContent = `${Math.round(successRate)}%`;
    donutSuccessCnt.textContent = successRuns;
    donutFailedCnt.textContent = failedRuns;

    const totalSegments = 219.9; // 2 * PI * r (r=35)
    
    // Success offset
    const successOffset = totalSegments - (successRate / 100) * totalSegments;
    donutSuccess.style.strokeDashoffset = successOffset;

    // Failed offset
    const failedRate = 100 - successRate;
    donutFailed.style.strokeDasharray = `${totalSegments}`;
    donutFailed.style.strokeDashoffset = `${totalSegments - (failedRate / 100) * totalSegments}`;
    
    // Rotate the failed segment to start right after success
    donutFailed.style.transform = `rotate(${(successRate / 100) * 360}deg)`;
    donutFailed.style.transformOrigin = "50px 50px";
}

// --- PIPELINES SNAPSHOTS & LINEAGE ---

async function fetchPipelineSnapshots() {
    try {
        const response = await fetch(`${API_BASE}/monitoring/pipelines?limit=200`);
        const result = await response.json();
        
        pipelineSnapshots.innerHTML = "";

        if (result.success && Array.isArray(result.data)) {
            const logs = result.data;
            if (logs.length === 0) {
                pipelineSnapshots.innerHTML = `<div class="empty-state">No pipeline data found</div>`;
                return;
            }

            // Group logs dynamically by pipeline name to compile counts
            const pipelinesMap = {};
            logs.forEach(log => {
                const name = log.pipeline_name;
                if (!pipelinesMap[name]) {
                    pipelinesMap[name] = {
                        pipeline_name: name,
                        total_runs: 0,
                        success_runs: 0,
                        failed_runs: 0,
                        last_run_timestamp: null
                    };
                }
                const p = pipelinesMap[name];
                p.total_runs += 1;
                if (log.status === "SUCCESS") p.success_runs += 1;
                else if (log.status === "FAILED") p.failed_runs += 1;
                
                // Compare timestamps
                if (log.start_time) {
                    const logTime = new Date(log.start_time).getTime();
                    if (!p.last_run_timestamp || logTime > new Date(p.last_run_timestamp).getTime()) {
                        p.last_run_timestamp = log.start_time;
                    }
                }
            });

            const list = Object.values(pipelinesMap);
            list.forEach(p => {
                const total = p.total_runs;
                const success = p.success_runs;
                const failed = p.failed_runs;
                const rate = total > 0 ? (success / total) * 100 : 100.0;
                
                let badgeClass = "rate-success";
                if (rate < 50) badgeClass = "rate-error";
                else if (rate < 90) badgeClass = "rate-warning";

                const row = document.createElement("div");
                row.className = "pipeline-snapshot-item animate-fade-in";
                row.innerHTML = `
                    <div class="pipeline-meta">
                        <h4>${p.pipeline_name}</h4>
                        <p>Last run: ${p.last_run_timestamp ? new Date(p.last_run_timestamp).toLocaleString() : 'N/A'}</p>
                    </div>
                    <div class="pipeline-runs-cnt">
                        <span class="snapshot-val">${total}</span>
                        <span class="snapshot-lbl">Total Runs</span>
                    </div>
                    <div class="pipeline-runs-cnt">
                        <span class="snapshot-val" style="color: var(--success);">${success}</span>
                        <span class="snapshot-lbl">Success</span>
                    </div>
                    <div class="pipeline-runs-cnt">
                        <span class="snapshot-val" style="color: var(--error);">${failed}</span>
                        <span class="snapshot-lbl">Failures</span>
                    </div>
                    <span class="pipeline-rate-badge ${badgeClass}">${rate.toFixed(1)}% Success</span>
                `;
                pipelineSnapshots.appendChild(row);
            });
        } else {
            pipelineSnapshots.innerHTML = `<div class="empty-state">Unable to load pipeline metrics</div>`;
        }
    } catch (e) {
        pipelineSnapshots.innerHTML = `<div class="empty-state" style="color: var(--error)">Failed to load pipelines list</div>`;
    }
}

function renderLineageFlow() {
    lineagePlaceholder.style.display = "none";
    lineageMermaidFlow.className = "mermaid-target active animate-fade-in";

    // Inject exact database dependency graph
    lineageMermaidFlow.innerHTML = `
flowchart LR
    CUSTOMER[("CUSTOMER")] --> Customer_Orders_Pipeline[["Customer_Orders_Pipeline"]];
    ORDERS[("ORDERS")] --> Customer_Orders_Pipeline;
    Customer_Orders_Pipeline --> CUSTOMER_ORDERS[("CUSTOMER_ORDERS")];
    ORDERS --> Sales_Report_Pipeline[["Sales_Report_Pipeline"]];
    PRODUCT[("PRODUCT")] --> Sales_Report_Pipeline;
    Sales_Report_Pipeline --> SALES_REPORT[("SALES_REPORT")];
    
    style CUSTOMER fill:#1E293B,stroke:#475569,stroke-width:2px;
    style ORDERS fill:#1E293B,stroke:#475569,stroke-width:2px;
    style PRODUCT fill:#1E293B,stroke:#475569,stroke-width:2px;
    style CUSTOMER_ORDERS fill:#0F172A,stroke:#6366F1,stroke-width:2px;
    style SALES_REPORT fill:#0F172A,stroke:#6366F1,stroke-width:2px;
    style Customer_Orders_Pipeline fill:#1E1B4B,stroke:#8B5CF6,stroke-width:2px;
    style Sales_Report_Pipeline fill:#1E1B4B,stroke:#8B5CF6,stroke-width:2px;
    `;

    try {
        mermaid.run({
            nodes: [lineageMermaidFlow]
        });
    } catch (err) {
        console.error("Mermaid compilation failed", err);
    }
}

// --- WEBHOOKS LIST ---

async function fetchAlertReceivers() {
    try {
        const response = await fetch(`${API_BASE}/alerts`);
        const result = await response.json();
        
        webhookList.innerHTML = "";
        
        const receivers = result.data?.webhooks || result.data || [];
        if (Array.isArray(receivers) && receivers.length > 0) {
            receivers.forEach(item => {
                const urlObj = new URL(item.url);
                const displayUrl = `${urlObj.hostname}/.../${urlObj.pathname.substring(urlObj.pathname.lastIndexOf('/') + 1)}`;

                const row = document.createElement("div");
                row.className = "alert-receiver-item animate-fade-in";
                row.innerHTML = `
                    <div class="alert-receiver-info">
                        <span class="alert-receiver-name" title="${item.url}">${displayUrl}</span>
                        <span class="alert-receiver-type">ID ${item.webhook_id} • Target: ${item.event_type}</span>
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
            appendSystemMessage(`Alert Webhook receiver ID ${id} was deleted successfully.`);
        }
    } catch (err) {
        alert("Failed to delete webhook receiver");
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
        const response = await fetch(`${API_BASE}/agents/copilot`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                message: text,
                conversation_id: conversationId || null
            })
        });

        const result = await response.json();
        removeTypingIndicator(typingIndicator);

        if (result.success) {
            if (!conversationId && result.conversation_id) {
                conversationId = result.conversation_id;
                localStorage.setItem("tusk_conversation_id", conversationId);
            }
            appendMessage(result.message, "assistant");
            
            // Refresh telemetry sidebar metrics if agents made database updates
            fetchTelemetry();
            fetchAlertReceivers();
            fetchPipelineSnapshots();
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
    const htmlContent = isAssistant ? formatMarkdown(text) : escapeHtml(text);

    msgBox.innerHTML = `
        <div class="message-avatar"><i data-lucide="${avatar}"></i></div>
        <div class="message-content">${htmlContent}</div>
    `;

    chatMessages.appendChild(msgBox);
    lucide.createIcons();

    if (isAssistant) {
        try {
            mermaid.run({
                nodes: msgBox.querySelectorAll('.mermaid')
            });
        } catch (e) {
            console.error("Mermaid compilation error", e);
        }
    }

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
                    <p>Hello! I'm Tusk, your ETL Observability Copilot. How can I help you today?</p>
                </div>
            </div>
        `;
        lucide.createIcons();
    }
}

function setBackendConnected(isConnected) {
    if (isConnected) {
        apiStatusDot.className = "pulse-indicator healthy";
        apiStatusText.textContent = "Backend Connected";
    } else {
        apiStatusDot.className = "pulse-indicator unhealthy";
        apiStatusText.textContent = "Offline / Connection Error";
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Client-side markdown + mermaid formatter
function formatMarkdown(text) {
    let html = text;

    const codeBlockRegex = /```(mermaid|sql|bash|json|python)?\s*([\s\S]*?)```/g;
    html = html.replace(codeBlockRegex, (match, lang, code) => {
        code = code.trim();
        if (lang === "mermaid") {
            return `<div class="mermaid">${code}</div>`;
        }
        return `<pre><code class="language-${lang || 'txt'}">${escapeHtml(code)}</code></pre>`;
    });

    const parts = html.split(/(<pre[\s\S]*?<\/pre>|<div class="mermaid">[\s\S]*?<\/div>)/);
    for (let i = 0; i < parts.length; i++) {
        if (!parts[i].startsWith('<pre') && !parts[i].startsWith('<div')) {
            let chunk = parts[i];
            
            chunk = chunk.replace(/^### (.*?)$/gm, '<h3>$1</h3>');
            chunk = chunk.replace(/^## (.*?)$/gm, '<h2>$1</h2>');
            chunk = chunk.replace(/^# (.*?)$/gm, '<h1>$1</h1>');
            
            chunk = chunk.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            chunk = chunk.replace(/\*(.*?)\*/g, '<em>$1</em>');
            
            chunk = chunk.replace(/`(.*?)`/g, '<code>$1</code>');
            
            chunk = chunk.replace(/^\*\s+(.*?)$/gm, '<li>$1</li>');
            chunk = chunk.replace(/^-\s+(.*?)$/gm, '<li>$1</li>');
            chunk = chunk.replace(/^\d+\.\s+(.*?)$/gm, '<li>$1</li>');
            
            chunk = chunk.replace(/(<li>.*?<\/li>)+/gs, (listMatch) => `<ul>${listMatch}</ul>`);
            
            chunk = chunk.replace(/\n\n/g, '</p><p>');
            chunk = chunk.replace(/\n/g, '<br>');
            
            parts[i] = chunk;
        }
    }

    html = parts.join('');
    
    if (!html.startsWith('<h') && !html.startsWith('<p') && !html.startsWith('<pre') && !html.startsWith('<ul')) {
        html = `<p>${html}</p>`;
    }
    
    return html;
}
