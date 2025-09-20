"""
Middleware to compensate for container time drift using real-time sync
"""

from django.utils import timezone
from datetime import datetime, timedelta
import requests
import logging
import threading
import time

logger = logging.getLogger(__name__)


class TimeOffsetMiddleware:
    """
    Dynamic middleware to compensate for Docker time drift
    Syncs with world time API every 5 minutes
    Remove this once the hosting provider fixes the time sync
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.time_offset = timedelta(0)
        self.last_sync = 0
        self.sync_interval = 300  # 5 minutes
        self.lock = threading.Lock()

        # Initial sync
        self._sync_time_offset()

    def _get_world_time(self):
        """Get current UTC time from world time API"""
        try:
            # Try multiple time sources for reliability (most reliable first)
            api_sources = [
                {
                    "url": "https://worldtimeapi.org/api/timezone/UTC",
                    "parser": lambda data: datetime.fromisoformat(
                        data["utc_datetime"].replace("Z", "+00:00")
                    ),
                },
                {
                    "url": "http://worldtimeapi.org/api/timezone/UTC",
                    "parser": lambda data: datetime.fromisoformat(
                        data["utc_datetime"].replace("Z", "+00:00")
                    ),
                },
                {
                    "url": "https://timeapi.io/api/Time/current/zone?timeZone=UTC",
                    "parser": lambda data: datetime.fromisoformat(
                        data["dateTime"] + "+00:00"
                    ),
                },
            ]

            # Try API sources first
            for source in api_sources:
                try:
                    response = requests.get(source["url"], timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        return source["parser"](data)
                except Exception as e:
                    logger.warning(f"Time sync failed for {source['url']}: {e}")
                    continue

            # Fallback: use HTTP date headers from reliable sites
            fallback_sites = [
                "https://www.google.com",
                "https://www.cloudflare.com",
                "https://httpbin.org/get",
                "https://www.github.com",
            ]

            from email.utils import parsedate_to_datetime

            for site in fallback_sites:
                try:
                    response = requests.head(site, timeout=3)
                    date_header = response.headers.get("Date")
                    if date_header:
                        return parsedate_to_datetime(date_header)
                except Exception as e:
                    logger.warning(f"HTTP date fallback failed for {site}: {e}")
                    continue

        except Exception as e:
            logger.error(f"All time sync methods failed: {e}")

        return None

    def _sync_time_offset(self):
        """Calculate and update the time offset"""
        try:
            world_time = self._get_world_time()
            if world_time:
                local_time = timezone.now()
                # Calculate offset (positive means local time is behind)
                new_offset = world_time.replace(tzinfo=local_time.tzinfo) - local_time

                # Only update if the change is reasonable (< 1 hour difference from previous)
                if abs((new_offset - self.time_offset).total_seconds()) < 3600:
                    self.time_offset = new_offset
                    self.last_sync = time.time()
                    logger.info(
                        f"Time sync successful. Offset: {self.time_offset.total_seconds():.2f} seconds"
                    )
                else:
                    logger.warning(
                        f"Time sync rejected - offset change too large: {new_offset.total_seconds():.2f}s"
                    )
            else:
                # If this is the very first sync and it fails, use a reasonable default
                if self.last_sync == 0:
                    logger.warning(
                        "Initial time sync failed, using 5-minute default offset"
                    )
                    self.time_offset = timedelta(minutes=5)
                    self.last_sync = time.time()
                else:
                    logger.warning("Time sync failed, keeping previous offset")
        except Exception as e:
            logger.error(f"Time sync error: {e}")
            # Fallback for first sync
            if self.last_sync == 0:
                self.time_offset = timedelta(minutes=5)
                self.last_sync = time.time()

    def __call__(self, request):
        # Check if we need to resync
        if time.time() - self.last_sync > self.sync_interval:
            # Do sync in background thread to avoid blocking requests
            def background_sync():
                with self.lock:
                    self._sync_time_offset()

            threading.Thread(target=background_sync, daemon=True).start()

        # Store original timezone.now on first request
        if not hasattr(timezone, "_original_now"):
            timezone._original_now = timezone.now

            # Override timezone.now to add our dynamic offset
            def corrected_now():
                return timezone._original_now() + self.time_offset

            timezone.now = corrected_now

        response = self.get_response(request)
        return response
