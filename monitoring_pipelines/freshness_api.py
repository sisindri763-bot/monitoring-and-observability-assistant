from fastapi import APIRouter, Query
from freshness_service import FreshnessService

router = APIRouter(prefix="/freshness", tags=["Freshness"])
service = FreshnessService()

@router.get("/status", summary="Get Freshness Status")
def get_freshness_status():
    return service.get_freshness_status()

@router.get("", summary="Get Freshness Status")
def get_freshness_status_root():
    return service.get_freshness_status()

@router.get("/{table_name}/trend", summary="Get Table Freshness Trend")
def get_table_freshness_trend(
    table_name: str,
    environment: str = Query(..., description="Either 'source' or 'target'")
):
    return service.get_table_freshness_trend(table_name, environment)
