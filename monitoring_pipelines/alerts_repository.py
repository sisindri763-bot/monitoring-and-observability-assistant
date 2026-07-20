import logging
from database import get_connection

logger = logging.getLogger(__name__)

class AlertsRepository:

    def _execute_query(self, query, params=None, fetch_one=False, is_write=False):
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            
            if is_write:
                conn.commit()
                return cursor.lastrowid
            
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

    def get_all_webhooks(self):
        query = "SELECT * FROM ALERT_WEBHOOKS"
        return self._execute_query(query)

    def register_webhook(self, url, event_type):
        query = """
        INSERT INTO ALERT_WEBHOOKS (url, event_type, status)
        VALUES (%s, %s, 'ACTIVE')
        """
        return self._execute_query(query, (url, event_type), is_write=True)

    def delete_webhook(self, webhook_id):
        query = "DELETE FROM ALERT_WEBHOOKS WHERE webhook_id = %s"
        return self._execute_query(query, (webhook_id,), is_write=True)
