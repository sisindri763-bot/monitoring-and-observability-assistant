import logging
from database import get_connection

logger = logging.getLogger(__name__)

class VolumeRepository:

    def _execute_query(self, query, params=None):
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except Exception as e:
            logger.exception(e)
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_latest_source_volumes(self):
        query = """
        SELECT 
            s1.table_name, 
            s1.row_count, 
            s1.collected_at
        FROM SOURCE_DB_METADATA s1
        INNER JOIN (
            SELECT table_name, MAX(collected_at) AS max_collected
            FROM SOURCE_DB_METADATA
            GROUP BY table_name
        ) s2 ON s1.table_name = s2.table_name AND s1.collected_at = s2.max_collected
        GROUP BY s1.table_name, s1.row_count, s1.collected_at
        """
        return self._execute_query(query)

    def get_latest_target_volumes(self):
        query = """
        SELECT 
            t1.table_name, 
            t1.row_count, 
            t1.collected_at
        FROM TARGET_DB_METADATA t1
        INNER JOIN (
            SELECT table_name, MAX(collected_at) AS max_collected
            FROM TARGET_DB_METADATA
            GROUP BY table_name
        ) t2 ON t1.table_name = t2.table_name AND t1.collected_at = t2.max_collected
        GROUP BY t1.table_name, t1.row_count, t1.collected_at
        """
        return self._execute_query(query)

    def get_source_table_history(self, table_name):
        query = """
        SELECT DISTINCT row_count, collected_at
        FROM SOURCE_DB_METADATA
        WHERE table_name = %s
        ORDER BY collected_at ASC
        """
        return self._execute_query(query, (table_name,))

    def get_target_table_history(self, table_name):
        query = """
        SELECT DISTINCT row_count, collected_at
        FROM TARGET_DB_METADATA
        WHERE table_name = %s
        ORDER BY collected_at ASC
        """
        return self._execute_query(query, (table_name,))
