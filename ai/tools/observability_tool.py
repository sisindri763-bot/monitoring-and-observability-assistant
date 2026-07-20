"""
Tusk Copilot - Observability Tool
Defines standard LangChain tools for retrieving data quality telemetry signals
(freshness, volume drift, system metrics, performance trends, lineage flow)
by invoking backend services directly.
"""

import logging
from langchain_core.tools import tool

# Direct service layer imports to avoid loopback HTTP deadlocks
from monitoring_pipelines.freshness_service import FreshnessService
from monitoring_pipelines.volume_service import VolumeService
from monitoring_pipelines.metrics_service import MetricsService
from monitoring_pipelines.monitoring_service import MonitoringService
from monitoring_pipelines.lineage_api import get_complete_lineage, get_pipeline_lineage

logger = logging.getLogger(__name__)

# Singletons for memory and connection reuse
_freshness_service = FreshnessService()
_volume_service = VolumeService()
_metrics_service = MetricsService()
_monitoring_service = MonitoringService()


@tool
def fetch_freshness_status() -> dict:
    """
    Fetches the data freshness status (latencies, table update times) for both source and target tables.
    Returns:
        A dictionary containing table freshness status details.
    """
    try:
        logger.info("[ObservabilityTool] Querying freshness status directly from service")
        return _freshness_service.get_freshness_status()
    except Exception as e:
        logger.exception(f"[ObservabilityTool] Failed to fetch freshness status: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_volume_status() -> dict:
    """
    Fetches volume status and row count anomalies between source and target tables.
    Returns:
        A dictionary containing row counts, percentage drift changes, and anomalies.
    """
    try:
        logger.info("[ObservabilityTool] Querying volume status directly from service")
        return _volume_service.get_volume_status()
    except Exception as e:
        logger.exception(f"[ObservabilityTool] Failed to fetch volume status: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_system_metrics() -> dict:
    """
    Fetches the system-wide execution metrics summary (total runs, failed runs, success rate, and durations).
    Returns:
        A dictionary containing overall metrics logs.
    """
    try:
        logger.info("[ObservabilityTool] Querying system metrics directly from service")
        return _monitoring_service.get_metrics()
    except Exception as e:
        logger.exception(f"[ObservabilityTool] Failed to fetch system metrics: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_throughput_trend() -> dict:
    """
    Fetches the hourly rows throughput trends from the metrics report API.
    Returns:
        A dictionary containing throughput timeline statistics.
    """
    try:
        logger.info("[ObservabilityTool] Querying throughput trends directly from service")
        return _metrics_service.get_hourly_throughput()
    except Exception as e:
        logger.exception(f"[ObservabilityTool] Failed to fetch throughput trends: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_executions_rate() -> dict:
    """
    Fetches the daily execution rates (success vs. failure counts and percentages) from the metrics report API.
    Returns:
        A dictionary containing daily status counts.
    """
    try:
        logger.info("[ObservabilityTool] Querying executions rate directly from service")
        return _metrics_service.get_daily_execution_rates()
    except Exception as e:
        logger.exception(f"[ObservabilityTool] Failed to fetch executions rate: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_pipeline_durations() -> dict:
    """
    Fetches execution run duration stats (average, min, max durations per pipeline) from the metrics report API.
    Returns:
        A dictionary listing durations metrics by pipeline name.
    """
    try:
        logger.info("[ObservabilityTool] Querying pipeline durations directly from service")
        return _metrics_service.get_pipeline_duration_trends()
    except Exception as e:
        logger.exception(f"[ObservabilityTool] Failed to fetch pipeline durations: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_lineage_flow() -> dict:
    """
    Fetches the dependency mapping graph showing the flow from source tables through pipelines to targets.
    Returns:
        A dictionary containing the flow node and edge definitions.
    """
    try:
        logger.info("[ObservabilityTool] Querying lineage flow directly from service")
        return get_complete_lineage()
    except Exception as e:
        logger.exception(f"[ObservabilityTool] Failed to fetch lineage flow: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_table_freshness_trend(table_name: str, environment: str) -> dict:
    """
    Fetches historical freshness delay/latency trends for a specific table in either 'source' or 'target' environment.
    Args:
        table_name: The name of the database table.
        environment: The environment type, either 'source' or 'target'.
    Returns:
        A dictionary containing the latency trend entries.
    """
    try:
        logger.info(f"[ObservabilityTool] Querying freshness trend for {table_name} ({environment}) directly from service")
        return _freshness_service.get_table_freshness_trend(table_name, environment)
    except Exception as e:
        logger.exception(f"[ObservabilityTool] Failed to fetch freshness trend: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_table_volume_trend(table_name: str, environment: str) -> dict:
    """
    Fetches historical row count volume trends for a specific table in either 'source' or 'target' environment.
    Args:
        table_name: The name of the database table.
        environment: The environment type, either 'source' or 'target'.
    Returns:
        A dictionary containing the historical row count entries.
    """
    try:
        logger.info(f"[ObservabilityTool] Querying volume trend for {table_name} ({environment}) directly from service")
        return _volume_service.get_table_volume_trend(table_name, environment)
    except Exception as e:
        logger.exception(f"[ObservabilityTool] Failed to fetch volume trend: {e}")
        return {"success": False, "error": str(e)}


@tool
def fetch_pipeline_lineage_details(pipeline_name: str) -> dict:
    """
    Fetches the specific source tables and target tables mapped to a single pipeline name.
    Args:
        pipeline_name: The name of the pipeline.
    Returns:
        A dictionary containing sources and targets arrays.
    """
    try:
        logger.info(f"[ObservabilityTool] Querying lineage details for {pipeline_name} directly from service")
        return get_pipeline_lineage(pipeline_name)
    except Exception as e:
        logger.exception(f"[ObservabilityTool] Failed to fetch lineage details for {pipeline_name}: {e}")
        return {"success": False, "error": str(e)}
