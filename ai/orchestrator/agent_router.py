"""
Tusk Copilot - Agent Router (Orchestrator)
Builds and compiles the LangGraph stateful graph.
Routes user queries to the correct agent nodes based on LLM intent classification.
"""

import os
import sys
import json
import urllib.request
import logging
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

# Add ai/ to path so agents can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage, AIMessage

from ..state import CopilotState
from ..agents.observability_agent import run_observability_agent
from ..agents.monitoring_agent import run_monitoring_agent
from ..agents.alerts_agent import run_alerts_agent

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# All valid agent names
AGENT_REGISTRY = {
    "observability": run_observability_agent,
    "monitoring": run_monitoring_agent,
    "alerts": run_alerts_agent,
}

# Intent -> Agent mapping with priority scores (higher score = stronger match)
INTENT_KEYWORDS = {
    "monitoring": [
        "failed", "failure", "failing", "error", "crash", "why", "fix", "resolve",
        "log", "logs", "history", "latest log", "execution", "executions",
        "recent", "search", "find", "pipeline ran", "ran", "status of",
        "dashboard", "summary", "overview", "successful", "success pipeline",
        "list pipelines", "how many pipelines", "all pipelines", "pipelines exist", "what pipelines", "pipeline count",
        "runs", "run details", "execution details", "errors", "crash logs", "why failed", "log trace", "traceback", "stack trace",
        "what pipelines do we have", "list out", "which pipelines"
    ],
    "observability": [
        "health", "health score", "stale", "freshness", "volume", "drift",
        "lineage", "throughput", "latency", "node", "dependency", "anomaly",
        "freshness trend", "volume trend", "pipeline durations", "execution rate",
        "duration", "run time", "latency", "delay", "stale tables", "drifted", "row count",
        "records per hour", "flow chart", "dependency map", "nodes", "edges", "connections", "mermaid", "health percent"
    ],
    "alerts": [
        "webhook", "alert", "receiver", "notification", "slack", "teams",
        "register", "add alert", "delete webhook", "remove alert", "alert channel",
        "slack channel", "alarm", "pagerduty", "teams channel", "alerting", "register webhook", "create webhook",
        "add alert channel", "remove webhook"
    ],
}


def _classify_intent_llm(user_query: str, chat_history: list) -> list[str]:
    """Call OpenRouter to classify which agents are needed, using chat history for context."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "openrouter/auto")
    if not api_key:
        return []

    system_prompt = (
        "You are the intent router for Tusk, an ETL pipeline observability AI assistant.\n"
        "Given the conversation history and a user's natural language question, determine which agents should run.\n"
        "Available agents:\n"
        "- observability: Telemetry aggregation (health score, freshness latency, volume drift, data lineage map, throughput).\n"
        "- monitoring: Log trace analysis, execution run history (failures, latest logs, log searches), and lists/configurations/counts of all pipelines.\n"
        "- alerts: Configures alarm channels/webhook receivers (register webhooks, list active webhooks, delete webhooks).\n\n"
        "IMPORTANT RULES:\n"
        "- Return ONLY a JSON array of agent names in execution order, e.g.: "
        '["monitoring", "observability"]\n'
        "If the query is general greeting, return an empty list [].\n"
        "No explanation. No markdown. Just the JSON array."
    )

    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history:
        role = "user" if msg.__class__.__name__ == "HumanMessage" else "assistant"
        messages.append({"role": role, "content": msg.get("content", str(msg)) if hasattr(msg, "get") else getattr(msg, "content", str(msg))})
    
    messages.append({"role": "user", "content": f"User question: {user_query}"})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.0
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Tusk ETL Observability Copilot"
    }
    try:
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload).encode(),
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read().decode())
            content = body["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            agents = json.loads(content.strip())
            if isinstance(agents, list):
                return [a for a in agents if a in AGENT_REGISTRY]
    except Exception as e:
        logger.error(f"[Router] LLM intent classification failed: {e}")
    return []


def _classify_intent_local(user_query: str) -> list[str]:
    """Score-based intent classification — picks all matching agents with score > 0."""
    query_lower = user_query.lower()
    
    # 🌟 GREETINGS / CONVERSATIONAL GREETINGS
    # If the user is just saying hello or introducing themselves, we don't execute any database agent nodes.
    # We let them pass directly to the synthesizer to generate a friendly, natural chat response.
    greeting_keywords = {"hi", "hello", "hey", "yo", "sup", "greetings", "morning", "afternoon", "evening"}
    words = set(query_lower.replace("?", "").replace("!", "").split())
    is_greeting = (
        not words.isdisjoint(greeting_keywords)
        or any(phrase in query_lower for phrase in ["my name is", "i am", "who are you", "what can you do", "help me"])
        or query_lower.strip() in ["hi", "hello", "hey", "help", "greet"]
    )
    
    # 🌟 Route general checkup / status questions to both monitoring and observability
    general_keywords = ["how", "status", "doing", "check", "system", "report", "overview", "okay", "ok", "state", "anything wrong", "issue", "problem", "happen"]
    is_general = any(kw in query_lower for kw in general_keywords) or not query_lower.strip()
    
    scores: dict[str, int] = {agent: 0 for agent in INTENT_KEYWORDS}

    for agent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in query_lower:
                # Multi-word keywords score higher
                scores[agent] += len(kw.split())

    best_score = max(scores.values())
    if best_score == 0:
        if is_greeting:
            return []  # Route directly to synthesizer for general greeting/chat response
        if is_general:
            return ["observability", "monitoring"]
        return ["monitoring"]  # Default: show execution status

    # Return all agents that matched (score > 0)
    matched_agents = [agent for agent, score in scores.items() if score > 0]
    if is_general:
        # Include both if a general keyword is present
        if "observability" not in matched_agents:
            matched_agents.append("observability")
        if "monitoring" not in matched_agents:
            matched_agents.append("monitoring")
            
    return matched_agents


# -------------------------------------------------------
# LangGraph Node Functions
# -------------------------------------------------------

def router_node(state: CopilotState) -> dict:
    """Intent classification node - decides which agents to run."""
    query = state.get("user_query", "")
    chat_history = state.get("chat_history", [])
    # Try LLM first, fall back to keywords
    agents = _classify_intent_llm(query, chat_history)
    if not agents:
        agents = _classify_intent_local(query)
    logger.info(f"[Router] Routing query to agents: {agents}")
    return {"active_agents": agents, "agent_context": {}}


def run_agent_node(agent_name: str):
    """Returns a node function that runs a specific agent."""
    def _node(state: CopilotState) -> dict:
        logger.info(f"[{agent_name.capitalize()}Agent] Running...")
        fn = AGENT_REGISTRY[agent_name]
        return fn(state)
    _node.__name__ = f"{agent_name}_node"
    return _node


def _build_fallback_response(query: str, context: dict) -> str:
    """
    Builds a clean, structured assistant response from raw agent findings
    when the LLM synthesizer is unavailable.
    """
    lines = ["## 🤖 Tusk Copilot Analysis\n"]

    # --- Monitoring findings ---
    mon = context.get("monitoring", {})
    if mon:
        lines.append("### 📋 Execution Monitoring\n")
        summary = mon.get("summary", "")
        if summary:
            lines.append(f"{summary}\n")

        if mon.get("failed_run_found"):
            lines.append(f"- **Pipeline:** `{mon.get('pipeline_name', 'Unknown')}`")
            lines.append(f"- **Execution ID:** {mon.get('execution_id', '-')}")
            lines.append(f"- **Error:** {mon.get('error_message', 'No message')}")
            log = mon.get("detailed_log")
            if log:
                lines.append(f"\n**Detailed Log:**\n```\n{str(log)[:800]}\n```")

        if mon.get("pipeline_history"):
            hist = mon["pipeline_history"]
            lines.append(f"- **Pipeline:** `{hist.get('pipeline_name', '')}`")
            data = hist.get("data", [])
            if isinstance(data, list):
                for run in data[:5]:
                    lines.append(
                        f"  - Run `{run.get('execution_id', '-')}` | "
                        f"Status: `{run.get('status', '-')}` | "
                        f"Started: {run.get('started_at', '-')}"
                    )

        if mon.get("failed_pipelines"):
            fp = mon["failed_pipelines"]
            items = fp.get("data", fp) if isinstance(fp, dict) else fp
            lines.append("\n**Failing Pipelines:**")
            for p in (items if isinstance(items, list) else [])[:10]:
                lines.append(f"  - `{p.get('pipeline_name', p)}`")

        if mon.get("dashboard_summary"):
            ds = mon["dashboard_summary"]
            data = ds.get("data", ds) if isinstance(ds, dict) else {}
            lines.append("\n**Dashboard Summary:**")
            for k, v in (data.items() if isinstance(data, dict) else []):
                lines.append(f"  - **{k.replace('_', ' ').title()}:** {v}")

    # --- Observability findings ---
    obs = context.get("observability", {})
    if obs:
        lines.append("\n### 🔭 Observability\n")
        state_label = obs.get("state", "UNKNOWN")
        health = obs.get("health_score", "N/A")
        emoji = "🟢" if state_label == "HEALTHY" else ("🟡" if state_label == "WARNING" else "🔴")
        lines.append(f"{emoji} **Health Score:** {health}/100 — **{state_label}**\n")
        lines.append(f"- **Success Rate:** {obs.get('success_rate', 'N/A')}%")
        lines.append(f"- **Freshness Score:** {obs.get('freshness_score_pct', 'N/A')}%")
        lines.append(f"- **Volume Score:** {obs.get('volume_score_pct', 'N/A')}%")
        lines.append(f"- **Stale Tables:** {len(obs.get('stale_tables', []))}")
        lines.append(f"- **Volume Anomalies:** {len(obs.get('volume_anomalies', []))}")
        lines.append(f"- **Lineage Nodes:** {obs.get('lineage_nodes_count', 0)}")

        if obs.get("stale_tables"):
            lines.append("\n**Stale Tables:**")
            for t in obs["stale_tables"][:5]:
                lines.append(f"  - `{t.get('table_name', t)}`")

        # 📊 RENDER PIPELINE DATA FLOW FLOWCHART
        lf = obs.get("lineage_flow", {})
        if lf and isinstance(lf, dict):
            nodes = lf.get("data", {}).get("nodes", []) or lf.get("nodes", [])
            edges = lf.get("data", {}).get("edges", []) or lf.get("edges", [])
            if nodes and edges:
                lines.append("\n**Pipeline Data Flow Flowchart Diagram:**\n")
                lines.append("```mermaid")
                lines.append("flowchart LR")
                for n in nodes:
                    nid = n.get("id", "")
                    label = n.get("label", nid)
                    ntype = n.get("type", "table")
                    if ntype == "pipeline":
                        lines.append(f"    {nid}[[\"{label}\"]]")
                    else:
                        lines.append(f"    {nid}[(\"{label}\")]")
                for e in edges:
                    src = e.get("source", "")
                    tgt = e.get("target", "")
                    lines.append(f"    {src} --> {tgt}")
                lines.append("```\n")

        # Render single pipeline details lineage map
        ld = obs.get("lineage_details", {})
        if ld and isinstance(ld, dict):
            pipeline_name = ld.get("pipeline_name", "")
            data = ld.get("data", {}).get("data", ld.get("data", {}))
            sources = data.get("sources", [])
            targets = data.get("targets", [])
            if sources or targets:
                lines.append(f"\n**Data Lineage Flow for `{pipeline_name}`:**\n")
                lines.append("```mermaid")
                lines.append("flowchart LR")
                lines.append(f"    {pipeline_name}[[\"{pipeline_name}\"]]")
                for src in sources:
                    lines.append(f"    {src}[(\"{src}\")] --> {pipeline_name}")
                for tgt in targets:
                    lines.append(f"    {pipeline_name} --> {tgt}[(\"{tgt}\")]")
                lines.append("```\n")

    # --- Alerts findings ---
    alerts = context.get("alerts", {})
    if alerts:
        lines.append("\n### 🔔 Alert Webhooks\n")
        summary = alerts.get("summary", "")
        if summary:
            lines.append(f"{summary}\n")
        receivers = alerts.get("webhooks", []) or alerts.get("receivers", [])
        if isinstance(receivers, list) and receivers:
            for r in receivers:
                lines.append(
                    f"  - **ID {r.get('webhook_id', '-')}** | Event Type: `{r.get('event_type', '-')}` | "
                    f"URL: `{r.get('url', '-')}`"
                )

    if not (mon or obs or alerts):
        lines.append("_No findings were returned by the agents. Please try a more specific question._")

    lines.append("\n---\n_Powered by Tusk Copilot — Multi-Agent ETL Observability Assistant_")
    return "\n".join(lines)


def synthesizer_node(state: CopilotState) -> dict:
    """
    Final node: compiles all agent outputs and calls the LLM to write
    the final human-friendly markdown response for the user.
    """
    query = state.get("user_query", "")
    context = state.get("agent_context", {})

    # Import lineage map to extract real-world pipelines and tables
    from monitoring_pipelines.lineage_config import LINEAGE_MAP
    
    # Extract list of pipelines and tables to guide LLM response and prevent hallucinations
    pipelines_list = list(LINEAGE_MAP.keys())
    tables_list = set()
    for mapping in LINEAGE_MAP.values():
        tables_list.update(mapping.get("sources", []))
        tables_list.update(mapping.get("targets", []))
    tables_list = list(tables_list)
    
    catalog_instruction = (
        f"IMPORTANT - YOUR SYSTEM GROUND TRUTH SCHEMA CATALOG:\n"
        f"You are monitoring exactly these two pipelines and five tables in the real database:\n"
        f"- Active Pipelines: {', '.join(f'`{p}`' for p in pipelines_list)}\n"
        f"- Active Tables: {', '.join(f'`{t}`' for t in tables_list)}\n"
        f"When showing example questions, greetings, lineage paths, or SQL queries, you MUST ONLY reference these exact pipelines and tables. "
        f"NEVER hallucinate or mention placeholder or example names (such as 'daily_sales_aggregation', 'customer_orders', or 'orders_count').\n\n"
    )

    # Serialize the complete structured findings from all agents
    try:
        context_block = json.dumps(context, indent=2)
    except Exception:
        context_block = str(context)

    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL", "openrouter/auto")

    response_text = ""

    if api_key:
        system_prompt = (
            "You are Tusk, an expert ETL pipeline monitoring and observability AI assistant.\n"
            "You analyze user questions regarding their ETL pipeline executions and telemetry data.\n\n"
            f"{catalog_instruction}"
            "CONVERSATIONAL RULE:\n"
            "If the Agent Findings context is empty, the user is likely greeting you (e.g. 'hello', 'hi'), asking general out-of-domain questions, or introducing themselves. "
            "In this case, respond in a very short, friendly, and concise manner (maximum 1 sentence/line, e.g., 'Hello Sasi! How can I help you today?'). "
            "Do NOT list out your capabilities, do NOT list, name, or mention any pipelines or tables, do NOT list example questions, and do NOT print bullet points. Keep it as a simple, direct welcome message.\n\n"
            "KEY TECHNICAL TASKS (If findings are present in the JSON context):\n"
            "1. Focus & Scope: You must ONLY answer the user's specific question. If they ask a simple count, list, or status question (e.g., 'how many pipelines exist'), answer only that question directly and concisely. Do NOT analyze failures, diagnose errors, recommend SQL fixes, or append a next-steps list unless they explicitly ask about errors, failures, why things failed, or how to fix issues.\n"
            "2. Health & Telemetry: Summarize the system health score, stale tables, or volume drift from observability when asked.\n"
            "3. Error Diagnosis: ONLY if the user asks about failures, errors, or diagnostics, analyze failed runs to diagnose the root cause (e.g., missing columns, syntax errors).\n"
            "4. SQL Fix Recommendation: ONLY if the user asks how to fix an error, write the exact, complete SQL queries or commands to run.\n"
            "5. Webhook Alerts: If the user asked about alerts, list webhooks or summarize actions.\n"
            "6. Data Lineage Flowchart: If the user asks about dependency flow or lineage, construct a Mermaid diagram.\n\n"
            "Be specific - cite exact table names and pipeline names from the JSON. Only include a next-steps list if the user specifically asked for troubleshooting/diagnostics advice."
        )
        user_prompt = (
            f"User Question: {query}\n\n"
            f"Agent Findings:\n{context_block}"
        )
        
        messages_payload = [{"role": "system", "content": system_prompt}]
        for msg in state.get("chat_history", []):
            role = "user" if msg.__class__.__name__ == "HumanMessage" else "assistant"
            messages_payload.append({"role": role, "content": msg.get("content", str(msg)) if hasattr(msg, "get") else getattr(msg, "content", str(msg))})
        
        messages_payload.append({"role": "user", "content": user_prompt})

        payload = {
            "model": model,
            "messages": messages_payload,
            "temperature": 0.4
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Tusk ETL Observability Copilot"
        }
        try:
            req = urllib.request.Request(
                OPENROUTER_URL,
                data=json.dumps(payload).encode(),
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                body = json.loads(resp.read().decode())
                response_text = body["choices"][0]["message"]["content"].strip()
        except Exception as e:
            logger.error(f"[Synthesizer] LLM call failed: {e}")

    if not response_text:
        response_text = _build_fallback_response(query, context)

    messages = list(state.get("messages", []))
    messages.append(AIMessage(content=response_text))

    return {
        "messages": messages,
        "agent_context": context
    }


def route_after_router(state: CopilotState):
    """Conditional edge: determines which agent nodes to visit after the router."""
    agents = state.get("active_agents", [])
    return agents[0] if agents else "synthesizer"


def route_after_agent(agent_name: str):
    """Conditional edge: after an agent runs, routes to next agent or synthesizer."""
    def _router(state: CopilotState):
        agents = state.get("active_agents", [])
        try:
            idx = agents.index(agent_name)
            if idx + 1 < len(agents):
                return agents[idx + 1]
        except ValueError:
            pass
        return "synthesizer"
    return _router


# -------------------------------------------------------
# Build and Compile the LangGraph Graph
# -------------------------------------------------------

def build_tusk_graph():
    """Builds and compiles the Tusk multi-agent stateful graph."""
    workflow = StateGraph(CopilotState)

    # Add router node
    workflow.add_node("router", router_node)

    # Add all agent nodes
    for agent_name in AGENT_REGISTRY:
        workflow.add_node(agent_name, run_agent_node(agent_name))

    # Add synthesizer node
    workflow.add_node("synthesizer", synthesizer_node)

    # Entry: always start at router
    workflow.add_edge(START, "router")

    # After router: conditional edge to first selected agent
    all_agent_names = list(AGENT_REGISTRY.keys()) + ["synthesizer"]
    workflow.add_conditional_edges("router", route_after_router, {a: a for a in all_agent_names})

    # After each agent: conditional edge to next agent or synthesizer
    for agent_name in AGENT_REGISTRY:
        workflow.add_conditional_edges(
            agent_name,
            route_after_agent(agent_name),
            {a: a for a in all_agent_names}
        )

    # Synthesizer always ends the graph
    workflow.add_edge("synthesizer", END)

    # Compile with in-memory session persistence (MemorySaver)
    memory = MemorySaver()
    graph = workflow.compile(checkpointer=memory)

    return graph


# Singleton compiled graph instance
tusk_graph = build_tusk_graph()
