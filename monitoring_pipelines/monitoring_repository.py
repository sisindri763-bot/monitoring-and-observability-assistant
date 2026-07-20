import logging
from datetime import datetime
from typing import Optional, List, Any
from database import get_connection

logger = logging.getLogger(__name__)

BASE_COLUMNS = """
execution_id,
pipeline_name,
status,
start_time,
end_time,
duration_sec,
rows_read,
rows_written,
error_message
"""

FULL_COLUMNS = BASE_COLUMNS + ", raw_log"


class MonitoringRepository:

    # ---------------------------------
    # 🔹 GENERIC QUERY EXECUTOR
    # ---------------------------------
    def _execute_query(self, query, params=None, fetch_one=False):
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())

            if fetch_one:
                return cursor.fetchone()
            return cursor.fetchall()

        except Exception as e:
            logger.exception(e)
            raise

        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # ---------------------------------
    # 🔹 ALL PIPELINES
    # ---------------------------------
    def get_all_pipelines(self, limit, offset):
        query = f"""
        SELECT {BASE_COLUMNS}
        FROM ETL_EXECUTION_LOG
        ORDER BY start_time DESC
        LIMIT %s OFFSET %s
        """
        return self._execute_query(query, (limit, offset))

    def get_all_pipelines_count(self):
        query = "SELECT COUNT(*) as total FROM ETL_EXECUTION_LOG"
        return self._execute_query(query, fetch_one=True)["total"]

    # ---------------------------------
    # 🔹 STATUS FILTER
    # ---------------------------------
    def get_pipelines_by_status(self, status, limit, offset):
        query = f"""
        SELECT {BASE_COLUMNS}
        FROM ETL_EXECUTION_LOG
        WHERE status = %s
        ORDER BY start_time DESC
        LIMIT %s OFFSET %s
        """
        return self._execute_query(query, (status, limit, offset))

    def get_failed_pipelines(self, limit, offset):
        return self.get_pipelines_by_status("FAILED", limit, offset)

    def get_successful_pipelines(self, limit, offset):
        return self.get_pipelines_by_status("SUCCESS", limit, offset)

    # ✅ COUNTS (FIXED)
    def get_failed_pipelines_count(self):
        query = """
        SELECT COUNT(*) AS total
        FROM ETL_EXECUTION_LOG
        WHERE status = 'FAILED'
        """
        result = self._execute_query(query, fetch_one=True)
        return result["total"] if result else 0

    def get_successful_pipelines_count(self):
        query = """
        SELECT COUNT(*) AS total
        FROM ETL_EXECUTION_LOG
        WHERE status = 'SUCCESS'
        """
        result = self._execute_query(query, fetch_one=True)
        return result["total"] if result else 0

    # ---------------------------------
    # 🔹 PIPELINE DETAILS
    # ---------------------------------
    def get_pipeline_details(self, pipeline_name):
        query = f"""
        SELECT {FULL_COLUMNS}
        FROM ETL_EXECUTION_LOG
        WHERE pipeline_name = %s
        ORDER BY start_time DESC
        LIMIT 1
        """
        return self._execute_query(query, (pipeline_name,), True)

    # ---------------------------------
    # 🔹 EXECUTION
    # ---------------------------------
    def get_execution(self, execution_id=None, pipeline_name=None):
        query = f"SELECT {FULL_COLUMNS} FROM ETL_EXECUTION_LOG WHERE 1=1"
        params = []

        if execution_id is not None:
            query += " AND execution_id = %s"
            params.append(execution_id)

        if pipeline_name:
            query += " AND pipeline_name = %s"
            params.append(pipeline_name)

        return self._execute_query(query, tuple(params), True)

    # ---------------------------------
    # 🔹 LOGS
    # ---------------------------------
    def get_latest_log(self, pipeline_name):
        query = f"""
        SELECT {FULL_COLUMNS}
        FROM ETL_EXECUTION_LOG
        WHERE pipeline_name = %s
        ORDER BY start_time DESC
        LIMIT 1
        """
        return self._execute_query(query, (pipeline_name,), True)

    def get_execution_log(self, execution_id):
        query = f"""
        SELECT {FULL_COLUMNS}
        FROM ETL_EXECUTION_LOG
        WHERE execution_id = %s
        """
        return self._execute_query(query, (execution_id,), True)

    # ---------------------------------
    # 🔹 SEARCH
    # ---------------------------------
    def search(self, keyword, limit, offset):
        keyword_param = f"%{keyword}%"

        query = f"""
        SELECT {FULL_COLUMNS}
        FROM ETL_EXECUTION_LOG
        WHERE pipeline_name LIKE %s
           OR status LIKE %s
           OR CAST(execution_id AS CHAR) LIKE %s
           OR error_message LIKE %s
           OR raw_log LIKE %s
        ORDER BY start_time DESC
        LIMIT %s OFFSET %s
        """

        return self._execute_query(
            query,
            (
                keyword_param,
                keyword_param,
                keyword_param,
                keyword_param,
                keyword_param,
                limit,
                offset,
            ),
        )

    def get_search_count(self, keyword):
        keyword_param = f"%{keyword}%"

        query = """
        SELECT COUNT(*) AS total
        FROM ETL_EXECUTION_LOG
        WHERE pipeline_name LIKE %s
           OR status LIKE %s
           OR CAST(execution_id AS CHAR) LIKE %s
           OR error_message LIKE %s
           OR raw_log LIKE %s
        """

        result = self._execute_query(
            query,
            (
                keyword_param,
                keyword_param,
                keyword_param,
                keyword_param,
                keyword_param,
            ),
            fetch_one=True,
        )
        return result["total"] if result else 0

    # ---------------------------------
    # 🔹 DASHBOARD
    # ---------------------------------
    def get_dashboard_summary(self):
        query = """
        SELECT
            COUNT(DISTINCT pipeline_name) AS total_pipelines,
            COUNT(*) AS total_executions,
            SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END) AS success_count,
            SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END) AS failed_count,
            SUM(CASE WHEN status='RUNNING' THEN 1 ELSE 0 END) AS running_count,
            ROUND(SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END)*100.0/COUNT(*),2) AS success_rate,
            ROUND(SUM(CASE WHEN status='FAILED' THEN 1 ELSE 0 END)*100.0/COUNT(*),2) AS failure_rate,
            AVG(NULLIF(duration_sec,0)) AS avg_runtime,
            MAX(duration_sec) AS max_runtime,
            MIN(NULLIF(duration_sec,0)) AS min_runtime,
            SUM(rows_read) AS total_rows_read,
            SUM(rows_written) AS total_rows_written,
            MAX(start_time) AS latest_execution,
            MIN(start_time) AS oldest_execution
        FROM ETL_EXECUTION_LOG
        """
        return self._execute_query(query, fetch_one=True)

    # ---------------------------------
    # 🔹 METRICS
    # ---------------------------------
    def get_metrics(self):
        query = """
        SELECT
            AVG(NULLIF(duration_sec,0)) AS avg_runtime,
            AVG(rows_read) AS avg_rows_read,
            AVG(rows_written) AS avg_rows_written,
            MAX(rows_read) AS max_rows_read,
            MAX(rows_written) AS max_rows_written,
            SUM(rows_read) AS total_rows_read,
            SUM(rows_written) AS total_rows_written,
            COUNT(*) AS total_executions,
            ROUND(SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END)*100.0/COUNT(*),2) AS success_rate
        FROM ETL_EXECUTION_LOG
        """
        return self._execute_query(query, fetch_one=True)

    # ---------------------------------
    # 🔹 HISTORY
    # ---------------------------------
    def get_pipeline_history(self, pipeline_name, from_date=None, to_date=None, limit=100, offset=0):
        query = f"""
        SELECT {BASE_COLUMNS}
        FROM ETL_EXECUTION_LOG
        WHERE pipeline_name = %s
        """
        params = [pipeline_name]

        if from_date:
            query += " AND start_time >= %s"
            params.append(from_date)

        if to_date:
            query += " AND start_time <= %s"
            params.append(to_date)

        query += " ORDER BY start_time DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        return self._execute_query(query, tuple(params))

    def get_pipeline_history_count(self, pipeline_name, from_date=None, to_date=None):
        query = """
        SELECT COUNT(*) as total
        FROM ETL_EXECUTION_LOG
        WHERE pipeline_name = %s
        """
        params = [pipeline_name]

        if from_date:
            query += " AND start_time >= %s"
            params.append(from_date)

        if to_date:
            query += " AND start_time <= %s"
            params.append(to_date)

        result = self._execute_query(query, tuple(params), True)
        return result["total"] if result else 0

    # ---------------------------------
    # 🔹 HEALTH CHECK
    # ---------------------------------
    def health_check(self):
        try:
            result = self._execute_query("SELECT 1 as status", fetch_one=True)
            return {"status": "healthy" if result else "unhealthy"}
        except:
            return {"status": "unhealthy"}