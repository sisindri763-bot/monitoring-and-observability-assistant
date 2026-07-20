import logging
from database import get_connection

logger = logging.getLogger(__name__)

class MetricsRepository:

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

    def get_hourly_throughput(self):
        query = """
        SELECT 
            DATE_FORMAT(start_time, '%Y-%m-%d %H:00:00') AS hour,
            SUM(rows_read) AS total_rows_read,
            SUM(rows_written) AS total_rows_written,
            COUNT(*) AS execution_count
        FROM ETL_EXECUTION_LOG
        GROUP BY hour
        ORDER BY hour ASC
        LIMIT 100
        """
        return self._execute_query(query)

    def get_daily_execution_rates(self):
        query = """
        SELECT 
            DATE(start_time) AS date,
            SUM(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) AS success_count,
            SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) AS failed_count,
            COUNT(*) AS total_count
        FROM ETL_EXECUTION_LOG
        GROUP BY date
        ORDER BY date ASC
        LIMIT 30
        """
        return self._execute_query(query)

    def get_pipeline_duration_trends(self):
        query = """
        SELECT 
            pipeline_name,
            AVG(NULLIF(duration_sec, 0)) AS avg_duration,
            MAX(duration_sec) AS max_duration,
            MIN(NULLIF(duration_sec, 0)) AS min_duration
        FROM ETL_EXECUTION_LOG
        GROUP BY pipeline_name
        """
        return self._execute_query(query)
