from fastapi import APIRouter, Query
from pydantic import BaseModel
from alerts_service import AlertsService

router = APIRouter(prefix="/alerts", tags=["Alerts & Webhooks"])
service = AlertsService()

class WebhookRegisterRequest(BaseModel):
    url: str
    event_type: str = "ALL"  # Can be 'ALL', 'FAILURES', or 'ANOMALIES'

@router.get("", summary="List Registered Alert Webhooks")
def get_webhooks():
    return service.get_webhooks()

@router.post("/register", summary="Register a New Alert Webhook")
def register_webhook(body: WebhookRegisterRequest):
    return service.register_webhook(body.url, body.event_type)

@router.delete("/{webhook_id}", summary="Delete an Alert Webhook")
def delete_webhook(webhook_id: int):
    return service.delete_webhook(webhook_id)
