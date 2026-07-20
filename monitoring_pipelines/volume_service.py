import logging
import math
from datetime import datetime, timezone
from volume_repository import VolumeRepository

logger = logging.getLogger(__name__)

class VolumeService:

    def __init__(self):
        self.repo = VolumeRepository()

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

    def get_volume_status(self):
        try:
            source_vols = self.repo.get_latest_source_volumes()
            target_vols = self.repo.get_latest_target_volumes()

            results = []

            # Process Source Volumes
            for row in source_vols:
                table = row["table_name"]
                count = row["row_count"]
                col_at = row["collected_at"]

                history = self.repo.get_source_table_history(table)
                history_counts = [h["row_count"] for h in history[:-1]] # exclude the current run from history

                is_anomalous = self._is_volume_anomalous(history_counts, count)
                
                prev_count = history_counts[-1] if history_counts else count
                change = count - prev_count
                pct_change = (change / prev_count * 100.0) if prev_count > 0 else 0.0

                results.append({
                    "table_name": table,
                    "environment": "source",
                    "row_count": count,
                    "previous_row_count": prev_count,
                    "change": change,
                    "percentage_change": round(pct_change, 2),
                    "collected_at": col_at.isoformat(),
                    "is_anomalous": is_anomalous,
                    "status": "ANOMALY" if is_anomalous else "GOOD"
                })

            # Process Target Volumes
            for row in target_vols:
                table = row["table_name"]
                count = row["row_count"]
                col_at = row["collected_at"]

                history = self.repo.get_target_table_history(table)
                history_counts = [h["row_count"] for h in history[:-1]]

                is_anomalous = self._is_volume_anomalous(history_counts, count)
                
                prev_count = history_counts[-1] if history_counts else count
                change = count - prev_count
                pct_change = (change / prev_count * 100.0) if prev_count > 0 else 0.0

                results.append({
                    "table_name": table,
                    "environment": "target",
                    "row_count": count,
                    "previous_row_count": prev_count,
                    "change": change,
                    "percentage_change": round(pct_change, 2),
                    "collected_at": col_at.isoformat(),
                    "is_anomalous": is_anomalous,
                    "status": "ANOMALY" if is_anomalous else "GOOD"
                })

            return self._success("Volume status and anomalies evaluated", results)

        except Exception as e:
            logger.exception(e)
            return self._error(f"Failed to evaluate volume status: {str(e)}")

    def get_table_volume_trend(self, table_name, environment):
        try:
            if environment == "source":
                history = self.repo.get_source_table_history(table_name)
            elif environment == "target":
                history = self.repo.get_target_table_history(table_name)
            else:
                return self._error("Invalid environment name. Use 'source' or 'target'")

            trend = []
            for h in history:
                trend.append({
                    "collected_at": h["collected_at"].isoformat(),
                    "row_count": h["row_count"]
                })

            return self._success(f"Volume history retrieved for {table_name}", trend)

        except Exception as e:
            logger.exception(e)
            return self._error(f"Failed to fetch volume trend: {str(e)}")

    def _is_volume_anomalous(self, history_counts, current_count):
        if not history_counts or len(history_counts) < 2:
            return False

        # Alert if row count drops to 0 when it previously had data
        if current_count == 0 and history_counts[-1] > 0:
            return True

        # Alert if count drops by >50% suddenly
        prev = history_counts[-1]
        if prev > 0 and current_count / prev < 0.5:
            return True

        # Calculate changes between successive history counts
        changes = []
        for i in range(1, len(history_counts)):
            changes.append(history_counts[i] - history_counts[i-1])

        if len(changes) < 2:
            # Not enough history of changes; standard check: deviation of current from prev count > 50%
            return abs(current_count - prev) > (prev * 0.5)

        mean = sum(changes) / len(changes)
        variance = sum((x - mean) ** 2 for x in changes) / len(changes)
        std_dev = math.sqrt(variance)

        # Minimum buffer deviation of 10 rows to prevent alerts on tiny updates
        std_dev = max(std_dev, 10.0)

        latest_change = current_count - prev
        return abs(latest_change - mean) > 3 * std_dev
