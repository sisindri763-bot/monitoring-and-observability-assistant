import logging
import json
import urllib.request
from datetime import datetime, timezone
from alerts_repository import AlertsRepository

logger = logging.getLogger(__name__)

class AlertsService:

    def __init__(self):
        self.repo = AlertsRepository()

    def _success(self, message, data):
        return {
            "success": True,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }

    def _error(self, message):
        return {
            "success": False,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def get_webhooks(self):
        try:
            webhooks = self.repo.get_all_webhooks()
            return self._success("Webhooks retrieved successfully", webhooks)
        except Exception as e:
            logger.exception(e)
            return self._error(f"Failed to fetch webhooks: {str(e)}")

    def register_webhook(self, url, event_type):
        try:
            if not url or not url.strip().startswith("http"):
                return self._error("Invalid Webhook URL format")
            if event_type not in ("ALL", "FAILURES", "ANOMALIES"):
                return self._error("Invalid event_type. Use 'ALL', 'FAILURES', or 'ANOMALIES'")

            webhook_id = self.repo.register_webhook(url, event_type)
            return self._success("Webhook registered successfully", {"webhook_id": webhook_id})
        except Exception as e:
            logger.exception(e)
            return self._error(f"Failed to register webhook: {str(e)}")

    def delete_webhook(self, webhook_id):
        try:
            self.repo.delete_webhook(webhook_id)
            return self._success("Webhook deleted successfully", {"webhook_id": webhook_id})
        except Exception as e:
            logger.exception(e)
            return self._error(f"Failed to delete webhook: {str(e)}")

    def dispatch_alert(self, event_type, payload):
        """
        Triggers HTTP POST payload dispatch to all registered active webhooks.
        """
        try:
            webhooks = self.repo.get_all_webhooks()
            dispatched = 0
            
            for hook in webhooks:
                if hook["status"] != "ACTIVE":
                    continue
                
                # Check if this hook is interested in the event
                if hook["event_type"] == "ALL" or hook["event_type"] == event_type:
                    url = hook["url"]
                    logger.info(f"Dispatching alert to webhook URL: {url}")
                    
                    try:
                        req_data = json.dumps({
                            "event_type": event_type,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "payload": payload
                        }).encode("utf-8")
                        
                        req = urllib.request.Request(
                            url,
                            data=req_data,
                            headers={"Content-Type": "application/json"}
                        )
                        
                        with urllib.request.urlopen(req, timeout=5) as response:
                            pass
                        dispatched += 1
                    except Exception as e:
                        logger.error(f"Failed to dispatch webhook to {url}: {e}")

            return dispatched

        except Exception as e:
            logger.exception(e)
            return 0
