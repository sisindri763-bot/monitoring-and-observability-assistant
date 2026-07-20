import logging
import math
from datetime import datetime, timezone
from monitoring_repository import MonitoringRepository

logger = logging.getLogger(__name__)


class MonitoringService:

    def __init__(self):
        self.repo = MonitoringRepository()

    # ---------------------------------
    # 🔹 STANDARD RESPONSE FORMAT
    # ---------------------------------
    def _success(self, message, data, pagination=None):
        response = {
            "success": True,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data
        }

        if pagination:
            response["pagination"] = pagination

        return response

    def _error(self, message):
        return {
            "success": False,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # ---------------------------------
    # 🔹 VALIDATIONS
    # ---------------------------------
    def _validate_pagination(self, limit, offset):
        if limit <= 0:
            raise ValueError("limit must be greater than 0")
        if offset < 0:
            raise ValueError("offset cannot be less than 0")

    def _validate_pipeline_name(self, pipeline_name):
        if not pipeline_name or not pipeline_name.strip():
            raise ValueError("pipeline_name cannot be empty")

    def _validate_dates(self, from_date, to_date):
        if from_date and to_date and from_date > to_date:
            raise ValueError("from_date cannot be greater than to_date")

    def _validate_execution_id(self, execution_id):
        if execution_id is None:
            raise ValueError("execution_id is required")
        if not isinstance(execution_id, int):
            raise ValueError("execution_id must be an integer")

    def _pagination_meta(self, limit, offset, total):
        return {
            "limit": limit,
            "offset": offset,
            "total_records": total,
            "total_pages": math.ceil(total / limit) if limit else 0,
            "current_page": (offset // limit) + 1 if limit else 1
        }

    # ---------------------------------
    # 🔹 DASHBOARD
    # ---------------------------------
    def get_dashboard_summary(self):
        try:
            data = self.repo.get_dashboard_summary()

            if not data:
                return self._error("No monitoring data found")

            return self._success(
                "Dashboard summary retrieved successfully",
                data
            )

        except Exception as e:
            logger.exception(e)
            return self._error("Unable to fetch dashboard summary")

    # ---------------------------------
    # 🔹 ALL PIPELINES
    # ---------------------------------
    def get_all_pipelines(self, limit=50, offset=0):
        try:
            self._validate_pagination(limit, offset)

            data = self.repo.get_all_pipelines(limit, offset)
            total = self.repo.get_all_pipelines_count()

            return self._success(
                "Pipelines retrieved successfully" if data else "No pipelines found",
                data,
                self._pagination_meta(limit, offset, total)
            )

        except ValueError as ve:
            return self._error(str(ve))
        except Exception as e:
            logger.exception(e)
            return self._error("Unable to fetch pipelines")

    # ---------------------------------
    # 🔹 PIPELINE DETAILS
    # ---------------------------------
    def get_pipeline_details(self, pipeline_name):
        try:
            self._validate_pipeline_name(pipeline_name)

            data = self.repo.get_pipeline_details(pipeline_name)

            if not data:
                return self._error("Pipeline not found")

            return self._success("Pipeline details retrieved successfully", data)

        except ValueError as ve:
            return self._error(str(ve))
        except Exception as e:
            logger.exception(e)
            return self._error("Unable to fetch pipeline details")

    # ---------------------------------
    # 🔹 PIPELINE HISTORY
    # ---------------------------------
    def get_pipeline_history(self, pipeline_name, from_date=None, to_date=None, limit=100, offset=0):
        try:
            self._validate_pipeline_name(pipeline_name)
            self._validate_pagination(limit, offset)
            self._validate_dates(from_date, to_date)

            data = self.repo.get_pipeline_history(
                pipeline_name, from_date, to_date, limit, offset
            )

            # ✅ FIXED (real total count with date filters)
            total = self.repo.get_pipeline_history_count(pipeline_name, from_date, to_date)

            return self._success(
                "Pipeline history retrieved successfully" if data else "No history found",
                data,
                self._pagination_meta(limit, offset, total)
            )

        except ValueError as ve:
            return self._error(str(ve))
        except Exception as e:
            logger.exception(e)
            return self._error("Unable to fetch pipeline history")

    # ---------------------------------
    # 🔹 FAILED PIPELINES
    # ---------------------------------
    def get_failed_pipelines(self, limit=50, offset=0):
        try:
            self._validate_pagination(limit, offset)

            data = self.repo.get_failed_pipelines(limit, offset)

            # ✅ FIXED (requires repo method)
            total = self.repo.get_failed_pipelines_count()

            return self._success(
                "Failed pipelines retrieved successfully" if data else "No failed pipelines found",
                data,
                self._pagination_meta(limit, offset, total)
            )

        except ValueError as ve:
            return self._error(str(ve))
        except Exception as e:
            logger.exception(e)
            return self._error("Unable to fetch failed pipelines")

    # ---------------------------------
    # 🔹 SUCCESS PIPELINES
    # ---------------------------------
    def get_successful_pipelines(self, limit=50, offset=0):
        try:
            self._validate_pagination(limit, offset)

            data = self.repo.get_successful_pipelines(limit, offset)

            # ✅ FIXED (requires repo method)
            total = self.repo.get_successful_pipelines_count()

            return self._success(
                "Successful pipelines retrieved successfully" if data else "No successful pipelines found",
                data,
                self._pagination_meta(limit, offset, total)
            )

        except ValueError as ve:
            return self._error(str(ve))
        except Exception as e:
            logger.exception(e)
            return self._error("Unable to fetch successful pipelines")

    # ---------------------------------
    # 🔹 EXECUTION LOOKUP
    # ---------------------------------
    def get_execution(self, execution_id=None, pipeline_name=None):
        try:
            if not execution_id and not pipeline_name:
                return self._error("Provide execution_id or pipeline_name")

            if execution_id:
                self._validate_execution_id(execution_id)

            data = self.repo.get_execution(execution_id, pipeline_name)

            if not data:
                return self._error("Execution not found")

            return self._success("Execution retrieved successfully", data)

        except ValueError as ve:
            return self._error(str(ve))
        except Exception as e:
            logger.exception(e)
            return self._error("Unable to fetch execution")

    # ---------------------------------
    # 🔹 LOGS
    # ---------------------------------
    def get_latest_log(self, pipeline_name):
        try:
            self._validate_pipeline_name(pipeline_name)

            data = self.repo.get_latest_log(pipeline_name)

            if not data:
                return self._error("Log not found")

            return self._success("Latest log retrieved successfully", data)

        except ValueError as ve:
            return self._error(str(ve))
        except Exception as e:
            logger.exception(e)
            return self._error("Unable to fetch latest log")

    def get_execution_log(self, execution_id):
        try:
            self._validate_execution_id(execution_id)

            data = self.repo.get_execution_log(execution_id)

            if not data:
                return self._error("Log not found")

            return self._success("Execution log retrieved successfully", data)

        except ValueError as ve:
            return self._error(str(ve))
        except Exception as e:
            logger.exception(e)
            return self._error("Unable to fetch execution log")

    # ---------------------------------
    # 🔹 METRICS
    # ---------------------------------
    def get_metrics(self):
        try:
            data = self.repo.get_metrics()

            if not data:
                return self._error("No metrics found")

            return self._success("Metrics retrieved successfully", data)

        except Exception as e:
            logger.exception(e)
            return self._error("Unable to fetch metrics")

    # ---------------------------------
    # 🔹 SEARCH
    # ---------------------------------
    def search(self, keyword, limit=50, offset=0):
        try:
            if not keyword:
                return self._error("keyword is required")

            self._validate_pagination(limit, offset)

            data = self.repo.search(keyword, limit, offset)
            total = self.repo.get_search_count(keyword)

            return self._success(
                "Search results retrieved successfully" if data else "No results found",
                data,
                self._pagination_meta(limit, offset, total)
            )

        except ValueError as ve:
            return self._error(str(ve))
        except Exception as e:
            logger.exception(e)
            return self._error("Search failed")

    # ---------------------------------
    # 🔹 HEALTH CHECK
    # ---------------------------------
    def health_check(self):
        try:
            data = self.repo.health_check()
            return self._success("Service is healthy", data)
        except Exception as e:
            logger.exception(e)
            return self._error("Service is unhealthy")