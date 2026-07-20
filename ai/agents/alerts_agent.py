"""
Tusk Copilot - Alerts Agent
Manages alerts webhook registration, deletion, and lookup using the monitoring_tool.
"""

import logging
import re

from ..tools.monitoring_tool import fetch_alert_receivers, register_alert_webhook, delete_alert_webhook

from ..state import CopilotState

logger = logging.getLogger(__name__)


def run_alerts_agent(state: CopilotState) -> dict:
    """
    Manages list, registration, and deletion of alert channels.
    """
    query = state.get("user_query", "").lower()
    context = state.get("agent_context", {})

    # Determine action based on keyword and query contents
    if ("register" in query or "add" in query or "create" in query) and re.search(r'https?://', query):
        # Extract URL from query
        urls = re.findall(r'https?://[^\s\)]+', state.get("user_query", ""))
        if urls:
            target_url = urls[0]
            # Determine event type if present
            event_type = "ALL"
            if "anomaly" in query or "anomalies" in query:
                event_type = "ANOMALIES"
            elif "failure" in query or "fail" in query or "failed" in query:
                event_type = "FAILURES"

            try:
                # 🚀 Real-time Webhook Dry-run connection validation ping
                import urllib.request
                import json
                ping_status = "Unknown"
                try:
                    test_payload = {
                        "text": "🤖 Tusk Observability Copilot: Alert Webhook registration verification ping."
                    }
                    req = urllib.request.Request(
                        target_url,
                        data=json.dumps(test_payload).encode(),
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req, timeout=3) as ping_r:
                        ping_status = f"Reachable (HTTP {ping_r.status})"
                except Exception as pe:
                    ping_status = f"Warning (Connection failed: {str(pe)[:80]})"

                res = register_alert_webhook.invoke({"url": target_url, "event_type": event_type})
                summary = (
                    f"Successfully registered new alert webhook receiver: {target_url} for events: {event_type}. "
                    f"Real-time connection test: {ping_status}."
                )
                context["alerts"] = {"result": res, "summary": summary}
            except Exception as e:
                logger.exception(f"[AlertsAgent] Registration failed: {e}")
                context["alerts"] = {"error": str(e), "summary": f"Failed to register alert webhook: {str(e)}"}
        else:
            context["alerts"] = {"summary": "Please provide a valid URL starting with http:// or https:// to register a webhook."}

    elif ("delete" in query or "remove" in query or "deregister" in query) and any(c.isdigit() for c in query):
        # Extract ID from query
        ids = re.findall(r'\b\d+\b', query)
        if ids:
            webhook_id = int(ids[0])
            try:
                res = delete_alert_webhook.invoke({"webhook_id": webhook_id})
                summary = f"Deregistered alert webhook receiver with ID {webhook_id}."
                context["alerts"] = {"result": res, "summary": summary}
            except Exception as e:
                logger.exception(f"[AlertsAgent] Deletion failed: {e}")
                context["alerts"] = {"error": str(e), "summary": f"Failed to delete webhook ID {webhook_id}: {str(e)}"}
        else:
            context["alerts"] = {"summary": "Please specify the ID of the webhook receiver you want to delete."}
    else:
        # Default: List Webhooks
        try:
            res = fetch_alert_receivers.invoke({})
            webhooks = res.get("data", []) if isinstance(res, dict) else res
            if webhooks:
                summary = f"Active Alert Channels: {len(webhooks)} configured webhooks: " + ", ".join(f"ID {w.get('webhook_id')}: {w.get('url')} ({w.get('event_type')})" for w in webhooks)
            else:
                summary = "No active alert webhook channels are configured."
            context["alerts"] = {"webhooks": webhooks, "summary": summary}
        except Exception as e:
            logger.exception(f"[AlertsAgent] Fetch failed: {e}")
            context["alerts"] = {"error": str(e), "summary": f"Failed to fetch alert channels: {str(e)}"}

    return {"agent_context": context}
