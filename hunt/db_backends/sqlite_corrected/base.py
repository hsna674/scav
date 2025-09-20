"""
Custom SQLite backend that corrects time at database level using the middleware offset
"""

from django.db.backends.sqlite3.base import DatabaseWrapper as SQLiteDatabaseWrapper
from django.utils import timezone
import datetime


class DatabaseWrapper(SQLiteDatabaseWrapper):
    """Custom SQLite wrapper with time correction that uses the middleware offset"""

    def get_new_connection(self, conn_params):
        """Override connection to add time correction functions"""
        conn = super().get_new_connection(conn_params)

        # Add custom SQL function to correct datetime('now') using global time patch
        def corrected_now():
            # Use Django's timezone.now() which is globally patched for time correction
            corrected_time = timezone.now()
            return corrected_time.strftime("%Y-%m-%d %H:%M:%S")

        # Add custom SQL function for corrected datetime comparisons
        def corrected_datetime(date_str):
            """Apply time offset to any datetime string for comparisons"""
            try:
                # Parse the input datetime
                dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                # Get the current offset from the global time correction
                corrected_now_dt = timezone.now()
                original_now_dt = timezone._original_now()
                offset = corrected_now_dt - original_now_dt
                # Apply offset to the input datetime
                corrected_dt = dt + offset
                return corrected_dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                # Return original if parsing fails
                return date_str

        conn.create_function("corrected_now", 0, corrected_now)
        conn.create_function("corrected_datetime", 1, corrected_datetime)

        return conn
