from fastapi import APIRouter, Query
from volume_service import VolumeService

router = APIRouter(prefix="/volume", tags=["Volume"])
service = VolumeService()

@router.get("/status", summary="Get Volume Status & Anomalies")
def get_volume_status():
    return service.get_volume_status()

@router.get("", summary="Get Volume Status & Anomalies")
def get_volume_status_root():
    return service.get_volume_status()

@router.get("/{table_name}/trend", summary="Get Table Volume Trend")
def get_table_volume_trend(
    table_name: str,
    environment: str = Query(..., description="Either 'source' or 'target'")
):
    return service.get_table_volume_trend(table_name, environment)
