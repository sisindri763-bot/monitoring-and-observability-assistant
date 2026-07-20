from fastapi import APIRouter
from metrics_service import MetricsService

router = APIRouter(prefix="/metrics-report", tags=["Advanced Metrics"])
service = MetricsService()

@router.get("/throughput-trend", summary="Get Throughput Trends")
def get_throughput_trend():
    return service.get_hourly_throughput()

@router.get("/executions-rate", summary="Get Executions Rate")
def get_executions_rate():
    return service.get_daily_execution_rates()

@router.get("/durations", summary="Get Pipeline Duration Trends")
def get_durations():
    return service.get_pipeline_duration_trends()
