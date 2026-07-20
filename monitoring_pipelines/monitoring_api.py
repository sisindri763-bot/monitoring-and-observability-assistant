from fastapi import APIRouter, Query
from datetime import datetime

from monitoring_service import MonitoringService


router = APIRouter(prefix="/monitoring", tags=["Monitoring"])
service = MonitoringService()

DEFAULT_LIMIT = 50
DEFAULT_OFFSET = 0


# ---------------------------
# Dashboard
# ---------------------------
@router.get("/dashboard/summary", summary="Dashboard Summary")
def get_dashboard_summary():
    return service.get_dashboard_summary()


# ---------------------------
# Pipelines
# ---------------------------
@router.get("/pipelines", summary="Get All Pipelines")
def get_all_pipelines(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=500),
    offset: int = Query(DEFAULT_OFFSET, ge=0),
):
    return service.get_all_pipelines(limit, offset)


@router.get("/pipelines/failed", summary="Get Failed Pipelines")
def get_failed_pipelines(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=500),
    offset: int = Query(DEFAULT_OFFSET, ge=0),
):
    return service.get_failed_pipelines(limit, offset)


@router.get("/pipelines/success", summary="Get Successful Pipelines")
def get_successful_pipelines(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=500),
    offset: int = Query(DEFAULT_OFFSET, ge=0),
):
    return service.get_successful_pipelines(limit, offset)


@router.get("/pipelines/{pipeline_name}", summary="Get Pipeline Details")
def get_pipeline_details(pipeline_name: str):
    return service.get_pipeline_details(pipeline_name)


@router.get("/pipelines/{pipeline_name}/history", summary="Get Pipeline History")
def get_pipeline_history(
    pipeline_name: str,
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=500),
    offset: int = Query(DEFAULT_OFFSET, ge=0),
):
    return service.get_pipeline_history(
        pipeline_name=pipeline_name,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )


@router.get("/pipelines/{pipeline_name}/latest-log", summary="Get Latest Pipeline Log")
def get_latest_log(pipeline_name: str):
    return service.get_latest_log(pipeline_name)


# ---------------------------
# Executions (✅ FIXED)
# ---------------------------
@router.get("/executions", summary="Get Execution")
def get_execution(
    execution_id: int | None = Query(None),
    pipeline_name: str | None = Query(None),
):
    return service.get_execution(
        execution_id=execution_id,
        pipeline_name=pipeline_name,
    )


@router.get("/executions/{execution_id}/log", summary="Get Execution Log")
def get_execution_log(execution_id: int):
    return service.get_execution_log(execution_id)


# ---------------------------
# Metrics
# ---------------------------
@router.get("/metrics", summary="Get System Metrics")
def get_metrics():
    return service.get_metrics()


# ---------------------------
# Search
# ---------------------------
@router.get("/search", summary="Search Pipelines and Executions")
def search(
    keyword: str = Query(
        ...,
        description="Pipeline name, status, execution id or error message"
    ),
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=500),
    offset: int = Query(DEFAULT_OFFSET, ge=0),
):
    return service.search(keyword, limit, offset)


# ---------------------------
# Health Check
# ---------------------------
@router.get("/health", summary="Health Check")
def health_check():
    return service.health_check()