"""
Tusk Copilot - Observability Agent (Programmatic)
Gathers and aggregates telemetry signals (freshness, volume, metrics, and lineage)
to compute real-time health scores without intermediate LLM overhead.
"""

import logging
import re
from typing import Any

from ..tools.observability_tool import (
    fetch_freshness_status,
    fetch_table_freshness_trend,
    fetch_volume_status,
    fetch_table_volume_trend,
    fetch_system_metrics,
    fetch_throughput_trend,
    fetch_executions_rate,
    fetch_pipeline_durations,
    fetch_lineage_flow,
    fetch_pipeline_lineage_details
)

from ..state import CopilotState

logger = logging.getLogger(__name__)

# Cast all tools to Any so Pylance does not flag .invoke() calls
_fetch_freshness_status: Any = fetch_freshness_status
_fetch_table_freshness_trend: Any = fetch_table_freshness_trend
_fetch_volume_status: Any = fetch_volume_status
_fetch_table_volume_trend: Any = fetch_table_volume_trend
_fetch_system_metrics: Any = fetch_system_metrics
_fetch_throughput_trend: Any = fetch_throughput_trend
_fetch_executions_rate: Any = fetch_executions_rate
_fetch_pipeline_durations: Any = fetch_pipeline_durations
_fetch_lineage_flow: Any = fetch_lineage_flow
_fetch_pipeline_lineage_details: Any = fetch_pipeline_lineage_details


def run_observability_agent(state: CopilotState) -> dict:
    """
    Programmatic telemetry aggregator for freshness, volume, metrics, and lineage.
    """
    query = state.get("user_query", "").lower()
    context = state.get("agent_context", {})

    # Initialize observability findings
    findings: dict[str, Any] = {
        "health_score": 100.0,
        "state": "HEALTHY",
        "stale_tables": [],
        "total_tables": 0,
        "volume_anomalies": [],
        "success_rate": 100.0,
        "lineage_nodes_count": 0
    }

    # 1. Handle specific trend queries
    if "freshness trend" in query or ("freshness" in query and "trend" in query):
        table_name = _extract_table_name(state.get("user_query", ""))
        if table_name:
            env = "target" if "target" in query else "source"
            try:
                trend = _fetch_table_freshness_trend.invoke({"table_name": table_name, "environment": env})
                findings["freshness_trend"] = {
                    "table_name": table_name,
                    "environment": env,
                    "data": trend
                }
            except Exception as e:
                logger.error(f"[ObservabilityAgent] Freshness trend error: {e}")

    if "volume trend" in query or ("volume" in query and "trend" in query):
        table_name = _extract_table_name(state.get("user_query", ""))
        if table_name:
            env = "target" if "target" in query else "source"
            try:
                trend = _fetch_table_volume_trend.invoke({"table_name": table_name, "environment": env})
                findings["volume_trend"] = {
                    "table_name": table_name,
                    "environment": env,
                    "data": trend
                }
            except Exception as e:
                logger.error(f"[ObservabilityAgent] Volume trend error: {e}")

    # 2. Handle pipeline lineage details queries
    if "lineage" in query and any(kw in query for kw in ["pipeline", "details", "for"]):
        pipeline_name = _extract_pipeline_name(state.get("user_query", ""))
        if pipeline_name:
            try:
                details = _fetch_pipeline_lineage_details.invoke({"pipeline_name": pipeline_name})
                findings["lineage_details"] = {
                    "pipeline_name": pipeline_name,
                    "data": details
                }
            except Exception as e:
                logger.error(f"[ObservabilityAgent] Lineage detail error: {e}")

    # 3. Handle advanced report trends
    if "throughput" in query:
        try:
            findings["throughput_trend"] = _fetch_throughput_trend.invoke({})
        except Exception:
            pass

    if "execution rate" in query or "success rate trend" in query:
        try:
            findings["executions_rate_trend"] = _fetch_executions_rate.invoke({})
        except Exception:
            pass

    if "duration" in query:
        try:
            findings["durations_trend"] = _fetch_pipeline_durations.invoke({})
        except Exception:
            pass

    # 4. Standard Health Telemetry Gathering
    try:
        # Freshness Status
        fd = _fetch_freshness_status.invoke({})
        items = fd.get("data", fd) if isinstance(fd, dict) else fd
        if isinstance(items, dict):
            items = items.get("tables", [])
        stale = [t for t in (items if isinstance(items, list) else [])
                 if "STALE" in str(t.get("freshness_status", "")).upper()]
        findings["stale_tables"] = stale
        findings["total_tables"] = len(items if isinstance(items, list) else [])
    except Exception as e:
        logger.error(f"[ObservabilityAgent] Freshness fetch error: {e}")

    try:
        # Volume Status
        vd = _fetch_volume_status.invoke({})
        items = vd.get("data", vd) if isinstance(vd, dict) else vd
        if isinstance(items, dict):
            items = items.get("tables", [])
        anomalies = [t for t in (items if isinstance(items, list) else [])
                     if t.get("anomaly_status") == "ANOMALY"]
        findings["volume_anomalies"] = anomalies
        findings["total_volume_tables"] = len(items if isinstance(items, list) else [])
    except Exception as e:
        logger.error(f"[ObservabilityAgent] Volume fetch error: {e}")

    try:
        # System Metrics
        md = _fetch_system_metrics.invoke({})
        metrics = md.get("data", md) if isinstance(md, dict) else {}
        findings["success_rate"] = float(metrics.get("success_rate", 100))
        findings["total_runs"] = int(metrics.get("total_runs", 0))
        findings["failed_runs"] = int(metrics.get("failed_runs", 0))
    except Exception as e:
        logger.error(f"[ObservabilityAgent] Metrics fetch error: {e}")

    try:
        # Lineage Flow
        lineage = _fetch_lineage_flow.invoke({})
        lineage_data = lineage.get("data", {}) if isinstance(lineage, dict) else {}
        findings["lineage_nodes_count"] = len(lineage_data.get("nodes", [])) if isinstance(lineage_data, dict) else 0
        findings["lineage_edges_count"] = len(lineage_data.get("edges", [])) if isinstance(lineage_data, dict) else 0
        
        # Save full lineage data for rendering flowchart diagrams in response
        if any(kw in query for kw in ["lineage", "flow", "graph", "dependency", "map"]):
            findings["lineage_flow"] = lineage
    except Exception as e:
        logger.error(f"[ObservabilityAgent] Lineage fetch error: {e}")

    # 5. Compute Mathematical Health Score
    stale_count: int = len(findings["stale_tables"])
    total_tables: int = max(int(findings["total_tables"]), 1)
    anomaly_count: int = len(findings["volume_anomalies"])
    total_vol: int = max(int(findings.get("total_volume_tables", 1)), 1)
    success_rate: float = float(findings["success_rate"])

    freshness_score: float = ((total_tables - stale_count) / total_tables) * 100
    volume_score: float = ((total_vol - anomaly_count) / total_vol) * 100
    health_score: float = round((success_rate * 0.5) + (freshness_score * 0.3) + (volume_score * 0.2), 1)

    state_label = "HEALTHY"
    if health_score < 70:
        state_label = "CRITICAL"
    elif health_score < 90:
        state_label = "WARNING"

    findings["health_score"] = health_score
    findings["state"] = state_label
    findings["freshness_score_pct"] = round(freshness_score, 1)
    findings["volume_score_pct"] = round(volume_score, 1)

    findings["summary"] = (
        f"Observability Status: {state_label} ({health_score}/100). "
        f"Pipeline Success Rate: {success_rate}%. "
        f"Stale Tables: {stale_count} of {total_tables}. "
        f"Volume Anomalies: {anomaly_count}. "
        f"Lineage Node Count: {findings['lineage_nodes_count']}."
    )

    context["observability"] = findings
    return {"agent_context": context}


def _extract_table_name(query: str) -> str | None:
    match = re.search(r'\b(?:table)\b\s+([a-zA-Z0-9_\-\.]+)', query, re.IGNORECASE)
    if match:
        return match.group(1)
    words = [w for w in query.replace("?", "").split() if "_" in w or "." in w]
    return words[0] if words else None


def _extract_pipeline_name(query: str) -> str | None:
    match = re.search(r'\b(?:pipeline|job)\b\s+([a-zA-Z0-9_\-\.]+)', query, re.IGNORECASE)
    if match:
        return match.group(1)
    return None
