import logging
from datetime import datetime, timezone
from metrics_repository import MetricsRepository

logger = logging.getLogger(__name__)

class MetricsService:

    def __init__(self):
        self.repo = MetricsRepository()

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

    def get_hourly_throughput(self):
        try:
            data = self.repo.get_hourly_throughput()
            return self._success("Hourly throughput metrics retrieved", data)
        except Exception as e:
            logger.exception(e)
            return self._error(f"Failed to fetch hourly throughput: {str(e)}")

    def get_daily_execution_rates(self):
        try:
            data = self.repo.get_daily_execution_rates()
            # Calculate percentages for response
            rates = []
            for row in data:
                total = float(row["total_count"]) if row["total_count"] is not None else 0.0
                success = float(row["success_count"]) if row["success_count"] is not None else 0.0
                failed = float(row["failed_count"]) if row["failed_count"] is not None else 0.0
                rates.append({
                    "date": str(row["date"]),
                    "success_count": int(success),
                    "failed_count": int(failed),
                    "total_count": int(total),
                    "success_rate_pct": round(success / total * 100.0, 2) if total > 0 else 0.0
                })
            return self._success("Daily execution status rates retrieved", rates)
        except Exception as e:
            logger.exception(e)
            return self._error(f"Failed to fetch daily execution rates: {str(e)}")

    def get_pipeline_duration_trends(self):
        try:
            data = self.repo.get_pipeline_duration_trends()
            formatted = []
            for row in data:
                formatted.append({
                    "pipeline_name": row["pipeline_name"],
                    "avg_duration_sec": round(float(row["avg_duration"]), 1) if row["avg_duration"] else None,
                    "max_duration_sec": row["max_duration"],
                    "min_duration_sec": row["min_duration"]
                })
            return self._success("Pipeline duration trends retrieved", formatted)
        except Exception as e:
            logger.exception(e)
            return self._error(f"Failed to fetch duration metrics: {str(e)}")
