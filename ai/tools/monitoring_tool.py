"""
Tusk Copilot - Monitoring Tool
Defines standard LangChain tools for retrieving execution logs, searching histories,
and managing webhook alert receivers by invoking backend services directly.
"""

import logging
from langchain_core.tools import tool

# Direct import of pipeline services to avoid loopback HTTP deadlocks
from monitoring_pipelines.monitoring_service import MonitoringService
from monitoring_pipelines.alerts_service import AlertsService

logger = logging.getLogger(__name__)

# Singletons for memory and connection reuse
_monitoring_service = MonitoringService()
_alerts_service = AlertsService()


@tool
def fetch_execution_logs() -> dict:
    """
    Fetches the history of pipeline executions to check statuses and extract failure messages.
    Returns:
        A dictionary containing the list of execution logs.
    """
    try:
        logger.info("[MonitoringTool] Querying execution logs directly from service")
        # Equivalent to /monitoring/executions?limit=20
        return _monitoring_service.get_execution()
    except Exception as e:
        logger.exception(f"[MonitoringTool] Failed to fetch execution logs: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_execution_log_detail(execution_id: int) -> dict:
    """
    Fetches the raw, detailed error logs for a specific pipeline execution ID.
    Args:
        execution_id: The unique ID of the pipeline execution run.
    Returns:
        A dictionary containing the execution log dump.
    """
    try:
        logger.info(f"[MonitoringTool] Querying log detail for ID {execution_id} directly from service")
        return _monitoring_service.get_execution_log(execution_id)
    except Exception as e:
        logger.exception(f"[MonitoringTool] Failed to fetch log detail for ID {execution_id}: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_dashboard_summary() -> dict:
    """
    Fetches the high-level dashboard summary (active pipeline counts, failure alerts, webhook configs).
    Returns:
        A dictionary containing summary counts.
    """
    try:
        logger.info("[MonitoringTool] Querying dashboard summary directly from service")
        return _monitoring_service.get_dashboard_summary()
    except Exception as e:
        logger.exception(f"[MonitoringTool] Failed to fetch dashboard summary: {e}")
        return {"success": False, "error": str(e)}


@tool
def list_etl_pipelines() -> dict:
    """
    Retrieves the complete list of all configured ETL pipelines in the observability backend.
    Returns:
        A dictionary listing the pipelines.
    """
    try:
        logger.info("[MonitoringTool] Querying pipelines list directly from service")
        return _monitoring_service.get_all_pipelines(limit=100)
    except Exception as e:
        logger.exception(f"[MonitoringTool] Failed to fetch pipelines list: {e}")
        return {"success": False, "error": str(e)}


@tool
def search_execution_logs(keyword: str) -> dict:
    """
    Searches pipeline names, status codes, execution IDs, or error logs matching a specific search keyword.
    Args:
        keyword: The keyword query string to search for (e.g. 'fail', 'Snowflake', 'CUSTOMER').
    Returns:
        A dictionary listing matching results.
    """
    try:
        logger.info(f"[MonitoringTool] Querying search logs for keyword '{keyword}' directly from service")
        return _monitoring_service.search(keyword, limit=50)
    except Exception as e:
        logger.exception(f"[MonitoringTool] Failed to search execution logs: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_alert_receivers() -> dict:
    """
    Fetches the list of all active Slack/Teams/Discord alert webhook channels configured in the system.
    Returns:
        A dictionary containing alert channels.
    """
    try:
        logger.info("[MonitoringTool] Querying alert receivers directly from service")
        return _alerts_service.get_webhooks()
    except Exception as e:
        logger.exception(f"[MonitoringTool] Failed to fetch alert receivers: {e}")
        return {"success": False, "error": str(e)}


@tool
def register_alert_webhook(url: str, event_type: str = "ALL") -> dict:
    """
    Registers a new webhook receiver URL to receive alerts on failures or anomalies.
    Args:
        url: The webhook handler endpoint URL.
        event_type: Alert filters scope ('ALL', 'FAILURES', or 'ANOMALIES').
    Returns:
        A dictionary confirming registration.
    """
    try:
        logger.info(f"[MonitoringTool] Registering webhook: {url} directly from service")
        return _alerts_service.register_webhook(url, event_type)
    except Exception as e:
        logger.exception(f"[MonitoringTool] Failed to register alert webhook: {e}")
        return {"success": False, "error": str(e)}


@tool
def delete_alert_webhook(webhook_id: int) -> dict:
    """
    Deregisters a webhook from the alerts notifications dispatch database by ID.
    Args:
        webhook_id: The unique database integer ID of the alert webhook.
    Returns:
        A dictionary confirming webhook removal status.
    """
    try:
        logger.info(f"[MonitoringTool] Deleting webhook ID {webhook_id} directly from service")
        return _alerts_service.delete_webhook(webhook_id)
    except Exception as e:
        logger.exception(f"[MonitoringTool] Failed to delete webhook ID {webhook_id}: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_failed_pipelines() -> dict:
    """
    Fetches the list of all currently failing ETL pipelines.
    Returns:
        A dictionary containing the list of failed pipelines.
    """
    try:
        logger.info("[MonitoringTool] Querying failed pipelines directly from service")
        return _monitoring_service.get_failed_pipelines()
    except Exception as e:
        logger.exception(f"[MonitoringTool] Failed to fetch failed pipelines: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_successful_pipelines() -> dict:
    """
    Fetches the list of all currently successful ETL pipelines.
    Returns:
        A dictionary containing the list of successful pipelines.
    """
    try:
        logger.info("[MonitoringTool] Querying successful pipelines directly from service")
        return _monitoring_service.get_successful_pipelines()
    except Exception as e:
        logger.exception(f"[MonitoringTool] Failed to fetch successful pipelines: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_pipeline_details(pipeline_name: str) -> dict:
    """
    Fetches the configuration and current status details for a specific pipeline name.
    Args:
        pipeline_name: The name of the pipeline.
    Returns:
        A dictionary containing pipeline status details.
    """
    try:
        logger.info(f"[MonitoringTool] Querying details for pipeline '{pipeline_name}' directly from service")
        return _monitoring_service.get_pipeline_details(pipeline_name)
    except Exception as e:
        logger.exception(f"[MonitoringTool] Failed to fetch pipeline details: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_pipeline_history(pipeline_name: str) -> dict:
    """
    Fetches the complete historical execution runs for a specific pipeline name.
    Args:
        pipeline_name: The name of the pipeline.
    Returns:
        A dictionary containing the execution logs history list.
    """
    try:
        logger.info(f"[MonitoringTool] Querying history for pipeline '{pipeline_name}' directly from service")
        return _monitoring_service.get_pipeline_history(pipeline_name, limit=100)
    except Exception as e:
        logger.exception(f"[MonitoringTool] Failed to fetch pipeline history: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_pipeline_latest_log(pipeline_name: str) -> dict:
    """
    Retrieves the most recent raw log file or log message for a specific pipeline.
    Args:
        pipeline_name: The name of the pipeline.
    Returns:
        A dictionary containing the latest log message.
    """
    try:
        logger.info(f"[MonitoringTool] Querying latest log for pipeline '{pipeline_name}' directly from service")
        return _monitoring_service.get_latest_log(pipeline_name)
    except Exception as e:
        logger.exception(f"[MonitoringTool] Failed to fetch latest pipeline log: {e}")
        return {"success": False, "error": str(e)}
