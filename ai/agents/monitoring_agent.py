"""
Tusk Copilot - Monitoring Agent (Programmatic)
Gathers pipeline execution runs, log search matches, failed/successful lists,
and retrieves detailed failure log dumps for diagnostic analysis without intermediate LLM overhead.
"""

import logging
import re
from typing import Any

from ..tools.monitoring_tool import (
    fetch_execution_logs,
    fetch_execution_log_detail,
    fetch_dashboard_summary,
    list_etl_pipelines,
    search_execution_logs,
    fetch_failed_pipelines,
    fetch_successful_pipelines,
    fetch_pipeline_details,
    fetch_pipeline_history,
    fetch_pipeline_latest_log
)

from ..state import CopilotState

logger = logging.getLogger(__name__)

_fetch_execution_logs: Any = fetch_execution_logs
_fetch_execution_log_detail: Any = fetch_execution_log_detail
_fetch_dashboard_summary: Any = fetch_dashboard_summary
_list_etl_pipelines: Any = list_etl_pipelines
_search_execution_logs: Any = search_execution_logs
_fetch_failed_pipelines: Any = fetch_failed_pipelines
_fetch_successful_pipelines: Any = fetch_successful_pipelines
_fetch_pipeline_details: Any = fetch_pipeline_details
_fetch_pipeline_history: Any = fetch_pipeline_history
_fetch_pipeline_latest_log: Any = fetch_pipeline_latest_log


def run_monitoring_agent(state: CopilotState) -> dict:
    """
    Programmatic execution monitoring and log trace aggregator.
    """
    query = state.get("user_query", "").lower()
    context = state.get("agent_context", {})

    findings: dict[str, Any] = {
        "failed_run_found": False,
        "logs_searched": False,
        "summary": "Execution states checked."
    }

    # 1. Pipeline History
    if "history" in query:
        pipeline_name = _extract_pipeline_name(state.get("user_query", ""))
        if pipeline_name:
            try:
                hist = _fetch_pipeline_history.invoke({"pipeline_name": pipeline_name})
                findings["pipeline_history"] = {
                    "pipeline_name": pipeline_name,
                    "data": hist
                }
                findings["summary"] = f"Pipeline history for '{pipeline_name}' fetched."
                context["monitoring"] = findings
                return {"agent_context": context}
            except Exception as e:
                logger.error(f"[MonitoringAgent] History error: {e}")

    # 2. Latest Pipeline Logs
    if "latest log" in query or "latest-log" in query:
        pipeline_name = _extract_pipeline_name(state.get("user_query", ""))
        if pipeline_name:
            try:
                latest_log = _fetch_pipeline_latest_log.invoke({"pipeline_name": pipeline_name})
                findings["latest_log"] = {
                    "pipeline_name": pipeline_name,
                    "data": latest_log
                }
                findings["summary"] = f"Latest log file for '{pipeline_name}' retrieved."
                context["monitoring"] = findings
                return {"agent_context": context}
            except Exception as e:
                logger.error(f"[MonitoringAgent] Latest log error: {e}")

    # 3. List Failed Pipelines
    if "failed pipeline" in query or "failing pipeline" in query:
        try:
            failed = _fetch_failed_pipelines.invoke({})
            findings["failed_pipelines"] = failed
            findings["summary"] = f"Failing pipelines fetched."
            context["monitoring"] = findings
            return {"agent_context": context}
        except Exception:
            pass

    # 4. List Successful Pipelines
    if "successful pipeline" in query or "success pipeline" in query:
        try:
            success = _fetch_successful_pipelines.invoke({})
            findings["successful_pipelines"] = success
            findings["summary"] = "Successful pipelines fetched."
            context["monitoring"] = findings
            return {"agent_context": context}
        except Exception:
            pass

    # 5. Search Executions & Logs
    if "search" in query or "find in logs" in query:
        keyword = _extract_search_keyword(state.get("user_query", ""))
        if keyword:
            try:
                search_results = _search_execution_logs.invoke({"keyword": keyword})
                findings["search_results"] = search_results
                findings["logs_searched"] = True
                findings["search_keyword"] = keyword
                findings["summary"] = f"Logs searched for keyword '{keyword}'."
                context["monitoring"] = findings
                return {"agent_context": context}
            except Exception:
                pass

    # 6. Dashboard Summary Overview
    if "dashboard" in query or "summary" in query or "overview" in query:
        try:
            summary_info = _fetch_dashboard_summary.invoke({})
            findings["dashboard_summary"] = summary_info
            findings["summary"] = "Dashboard summary statistics retrieved."
            context["monitoring"] = findings
            return {"agent_context": context}
        except Exception:
            pass

    # 7. Standard Execution failure diagnostics (retrieve logs + detailed error trace)
    try:
        logs_res = _fetch_execution_logs.invoke({})
        executions = logs_res.get("data", []) if isinstance(logs_res, dict) else logs_res
        if not isinstance(executions, list):
            executions = []

        # Find the most recent failed execution
        failed_run = None
        target_pipeline = _extract_pipeline_name(state.get("user_query", ""))
        for run in executions:
            status = str(run.get("status", "")).upper()
            if status in ("FAILED", "ERROR", "FAILURE"):
                if not target_pipeline or target_pipeline.lower() == str(run.get("pipeline_name", "")).lower():
                    failed_run = run
                    break

        if failed_run:
            exec_id = failed_run.get("execution_id")
            pipeline_name = failed_run.get("pipeline_name")
            error_msg = failed_run.get("error_message", "")

            # Retrieve full execution trace log
            detail_res = _fetch_execution_log_detail.invoke({"execution_id": exec_id})
            detailed_log = detail_res.get("data", detail_res) if isinstance(detail_res, dict) else detail_res

            findings["failed_run_found"] = True
            findings["pipeline_name"] = pipeline_name
            findings["execution_id"] = exec_id
            findings["error_message"] = error_msg
            findings["detailed_log"] = detailed_log
            findings["summary"] = f"Pipeline '{pipeline_name}' failed (Run {exec_id}). Error: {error_msg}. Log details gathered."

            # Save failed pipeline to allow observability agent to perform target lineage lookup
            context["failed_pipeline"] = pipeline_name
        else:
            pipelines = _list_etl_pipelines.invoke({})
            findings["pipelines"] = pipelines
            findings["summary"] = "No failed pipeline executions detected. Pipeline listing retrieved."

    except Exception as e:
        logger.error(f"[MonitoringAgent] Standard executions query error: {e}")
        findings["error"] = str(e)
        findings["summary"] = "Execution history check failed."

    context["monitoring"] = findings
    return {"agent_context": context}


def _extract_pipeline_name(query: str) -> str | None:
    match = re.search(r'\b(?:pipeline|job)\b\s+([a-zA-Z0-9_\-\.]+)', query, re.IGNORECASE)
    if match:
        return match.group(1)
    for word in query.split():
        if "pipeline" in word.lower() and len(word) > 8:
            return word.strip("?,.()\"'")
    return None


def _extract_search_keyword(query: str) -> str | None:
    match = re.search(r'\b(?:search|find)\b\s+(?:for\s+)?([a-zA-Z0-9_\-\.]+)', query, re.IGNORECASE)
    if match:
        return match.group(1)
    words = query.split()
    return words[-1].strip("?,.()\"'") if words else None
