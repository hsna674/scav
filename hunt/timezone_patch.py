"""
Early timezone patching to ensure time correction is applied before any database operations.
This must be imported before Django fully loads to ensure all timezone.now() calls use corrected time.
"""

from django.utils import timezone
from datetime import timedelta
import logging
import threading
import time
import requests
from datetime import datetime

logger = logging.getLogger(__name__)

# Global time offset and sync state
_time_offset = timedelta(minutes=5)  # Default 5-minute offset for production server
_last_sync = 0
_sync_interval = 300  # 5 minutes
_sync_lock = threading.Lock()

# Store original timezone.now before patching
if not hasattr(timezone, "_original_now"):
    timezone._original_now = timezone.now


def get_world_time():
    """Get current UTC time from world time API - simplified version"""
    try:
        # Try the most reliable source first
        response = requests.get("https://worldtimeapi.org/api/timezone/UTC", timeout=3)
        if response.status_code == 200:
            data = response.json()
            return datetime.fromisoformat(data["utc_datetime"].replace("Z", "+00:00"))
    except Exception:
        pass

    # Fallback to HTTP headers
    try:
        response = requests.head("https://www.google.com", timeout=2)
        date_header = response.headers.get("Date")
        if date_header:
            from email.utils import parsedate_to_datetime

            return parsedate_to_datetime(date_header)
    except Exception:
        pass

    return None


def sync_time_offset():
    """Sync the global time offset"""
    global _time_offset, _last_sync

    try:
        world_time = get_world_time()
        if world_time:
            local_time = timezone._original_now()

            # Ensure both times are timezone-aware and comparable
            if world_time.tzinfo is None:
                world_time = world_time.replace(tzinfo=local_time.tzinfo)
            elif local_time.tzinfo is None:
                local_time = local_time.replace(tzinfo=world_time.tzinfo)

            # Calculate offset (positive means local time is behind)
            new_offset = world_time - local_time

            # Only update if the change is reasonable (< 1 hour difference from previous)
            if abs((new_offset - _time_offset).total_seconds()) < 3600:
                old_offset = _time_offset.total_seconds()
                _time_offset = new_offset
                _last_sync = time.time()
                logger.info(
                    f"Time sync successful. Offset changed from {old_offset:.2f}s to {new_offset.total_seconds():.2f}s"
                )
            else:
                logger.warning(
                    f"Time sync rejected - offset change too large: {new_offset.total_seconds():.2f}s"
                )
        else:
            if _last_sync == 0:
                logger.warning(
                    f"Initial time sync failed, using default offset: {_time_offset.total_seconds():.2f}s"
                )
                _last_sync = time.time()
            else:
                logger.warning(
                    f"Time sync failed, keeping previous offset: {_time_offset.total_seconds():.2f}s"
                )
    except Exception as e:
        logger.error(f"Time sync error: {e}")
        if _last_sync == 0:
            logger.warning(
                f"Time sync error on first sync, using default offset: {_time_offset.total_seconds():.2f}s"
            )
            _last_sync = time.time()


def corrected_now():
    """Return current time with offset applied"""
    global _last_sync, _sync_interval

    # Check if we need to resync (but don't block)
    if time.time() - _last_sync > _sync_interval:

        def background_sync():
            with _sync_lock:
                sync_time_offset()

        threading.Thread(target=background_sync, daemon=True).start()

    return timezone._original_now() + _time_offset


# Patch timezone.now immediately when this module is imported
timezone.now = corrected_now

# Do initial sync
sync_time_offset()

logger.info(
    f"Time correction system initialized with {_time_offset.total_seconds():.2f}s offset"
)
