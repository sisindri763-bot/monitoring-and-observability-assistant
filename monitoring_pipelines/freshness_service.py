import logging
import math
from datetime import datetime, timezone
from freshness_repository import FreshnessRepository

logger = logging.getLogger(__name__)

class FreshnessService:

    def __init__(self):
        self.repo = FreshnessRepository()

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

    def get_freshness_status(self):
        try:
            source_updates = self.repo.get_latest_source_updates()
            target_updates = self.repo.get_latest_target_updates()
            
            results = []
            now = datetime.now()

            # Process Source tables
            for row in source_updates:
                table = row["table_name"]
                last_updated = row["last_updated"]
                collected_at = row["collected_at"]

                history = self.repo.get_source_table_history(table)
                latencies = []
                for h in history:
                    if h["last_updated"] and h["collected_at"]:
                        latencies.append((h["collected_at"] - h["last_updated"]).total_seconds())

                current_latency = 0
                if last_updated:
                    # Current latency in seconds since last update
                    current_latency = (now - last_updated).total_seconds()
                
                is_anomalous = False
                if last_updated:
                    is_anomalous = self._is_latency_anomalous(latencies, current_latency)

                results.append({
                    "table_name": table,
                    "environment": "source",
                    "last_updated": last_updated.isoformat() if last_updated else None,
                    "collected_at": collected_at.isoformat(),
                    "current_latency_sec": int(current_latency) if last_updated else None,
                    "is_anomalous": is_anomalous,
                    "status": "ANOMALY" if is_anomalous else ("GOOD" if last_updated else "UNKNOWN")
                })

            # Process Target tables
            for row in target_updates:
                table = row["table_name"]
                last_updated = row["last_updated"]
                collected_at = row["collected_at"]

                # Snowflake datetime might be offset-aware, convert to naive for calculations
                if last_updated and last_updated.tzinfo is not None:
                    last_updated = last_updated.replace(tzinfo=None)

                history = self.repo.get_target_table_history(table)
                latencies = []
                for h in history:
                    h_update = h["last_updated"]
                    if h_update and h_update.tzinfo is not None:
                        h_update = h_update.replace(tzinfo=None)
                    if h_update and h["collected_at"]:
                        latencies.append((h["collected_at"] - h_update).total_seconds())

                current_latency = 0
                if last_updated:
                    current_latency = (now - last_updated).total_seconds()

                is_anomalous = False
                if last_updated:
                    is_anomalous = self._is_latency_anomalous(latencies, current_latency)

                results.append({
                    "table_name": table,
                    "environment": "target",
                    "last_updated": last_updated.isoformat() if last_updated else None,
                    "collected_at": collected_at.isoformat(),
                    "current_latency_sec": int(current_latency) if last_updated else None,
                    "is_anomalous": is_anomalous,
                    "status": "ANOMALY" if is_anomalous else ("GOOD" if last_updated else "UNKNOWN")
                })

            return self._success("Freshness status evaluated successfully", results)

        except Exception as e:
            logger.exception(e)
            return self._error(f"Failed to evaluate freshness status: {str(e)}")

    def get_table_freshness_trend(self, table_name, environment):
        try:
            if environment == "source":
                history = self.repo.get_source_table_history(table_name)
            elif environment == "target":
                history = self.repo.get_target_table_history(table_name)
            else:
                return self._error("Invalid environment name. Use 'source' or 'target'")

            trend = []
            for h in history:
                last_up = h["last_updated"]
                col_at = h["collected_at"]
                
                if last_up and last_up.tzinfo is not None:
                    last_up = last_up.replace(tzinfo=None)
                
                latency = None
                if last_up and col_at:
                    latency = int((col_at - last_up).total_seconds())

                trend.append({
                    "collected_at": col_at.isoformat(),
                    "last_updated": last_up.isoformat() if last_up else None,
                    "latency_sec": latency
                })

            return self._success(f"Freshness trend retrieved for {table_name}", trend)

        except Exception as e:
            logger.exception(e)
            return self._error(f"Failed to fetch freshness trend: {str(e)}")

    def _is_latency_anomalous(self, latencies, current_latency):
        if not latencies or len(latencies) < 3:
            # Fallback default: Stale if latency is > 24 hours (86400 seconds)
            return current_latency > 86400

        mean = sum(latencies) / len(latencies)
        variance = sum((x - mean) ** 2 for x in latencies) / len(latencies)
        std_dev = math.sqrt(variance)

        # Minimum buffer of 30 minutes (1800s) to avoid false positives for highly stable tables
        std_dev = max(std_dev, 1800.0)

        threshold = mean + 3 * std_dev
        return current_latency > threshold
