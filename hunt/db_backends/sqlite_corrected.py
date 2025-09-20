"""
Custom SQLite backend that corrects time at database level
"""

from django.db.backends.sqlite3.base import DatabaseWrapper as SQLiteDatabaseWrapper
import datetime


class DatabaseWrapper(SQLiteDatabaseWrapper):
    """Custom SQLite wrapper with time correction"""

    def get_new_connection(self, conn_params):
        """Override connection to add time correction functions"""
        conn = super().get_new_connection(conn_params)

        # Add custom SQL function to correct datetime('now')
        def corrected_now():
            # Get current time and add 321 seconds (5 min 21 sec offset)
            now = datetime.datetime.utcnow()
            corrected = now + datetime.timedelta(seconds=321)
            return corrected.strftime("%Y-%m-%d %H:%M:%S")

        conn.create_function("corrected_now", 0, corrected_now)
        return conn
