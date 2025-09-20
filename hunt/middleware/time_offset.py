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

        # Set a default 5-minute offset immediately for production server timing issues
        self.time_offset = timedelta(minutes=5)

        # Override timezone.now immediately, not on first request
        if not hasattr(timezone, "_original_now"):
            timezone._original_now = timezone.now

            # Override timezone.now to add our dynamic offset
            def corrected_now():
                return timezone._original_now() + self.time_offset

            timezone.now = corrected_now
            logger.info(
                f"Time correction middleware initialized with default {self.time_offset.total_seconds():.2f}s offset"
            )

        # Initial sync after setting up the override (will refine the offset)
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
                    response = requests.get(source["url"], timeout=3)
                    if response.status_code == 200:
                        data = response.json()
                        world_time = source["parser"](data)
                        logger.debug(
                            f"Time sync successful from {source['url']}: {world_time}"
                        )
                        return world_time
                except Exception as e:
                    logger.debug(f"Time sync failed for {source['url']}: {e}")
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
                    response = requests.head(site, timeout=2)
                    date_header = response.headers.get("Date")
                    if date_header:
                        world_time = parsedate_to_datetime(date_header)
                        logger.debug(
                            f"Time sync successful from HTTP headers {site}: {world_time}"
                        )
                        return world_time
                except Exception as e:
                    logger.debug(f"HTTP date fallback failed for {site}: {e}")
                    continue

        except Exception as e:
            logger.error(f"All time sync methods failed: {e}")

        return None

    def _sync_time_offset(self):
        """Calculate and update the time offset"""
        try:
            world_time = self._get_world_time()
            if world_time:
                # Use the original (non-corrected) time for calculating offset
                local_time = (
                    timezone._original_now()
                    if hasattr(timezone, "_original_now")
                    else timezone.now()
                )

                # Ensure both times are timezone-aware and comparable
                if world_time.tzinfo is None:
                    world_time = world_time.replace(tzinfo=local_time.tzinfo)
                elif local_time.tzinfo is None:
                    local_time = local_time.replace(tzinfo=world_time.tzinfo)

                # Calculate offset (positive means local time is behind)
                new_offset = world_time - local_time

                # Only update if the change is reasonable (< 1 hour difference from previous)
                if abs((new_offset - self.time_offset).total_seconds()) < 3600:
                    old_offset = self.time_offset.total_seconds()
                    self.time_offset = new_offset
                    self.last_sync = time.time()
                    logger.info(
                        f"Time sync successful. Offset changed from {old_offset:.2f}s to {self.time_offset.total_seconds():.2f}s"
                    )
                else:
                    logger.warning(
                        f"Time sync rejected - offset change too large: {new_offset.total_seconds():.2f}s (current: {self.time_offset.total_seconds():.2f}s)"
                    )
            else:
                # If this is the very first sync and it fails, keep the default offset
                if self.last_sync == 0:
                    logger.warning(
                        f"Initial time sync failed, keeping default offset: {self.time_offset.total_seconds():.2f}s"
                    )
                    self.last_sync = time.time()
                else:
                    logger.warning(
                        f"Time sync failed, keeping previous offset: {self.time_offset.total_seconds():.2f}s"
                    )
        except Exception as e:
            logger.error(f"Time sync error: {e}")
            # Fallback for first sync - keep the default offset
            if self.last_sync == 0:
                logger.warning(
                    f"Time sync error on first sync, keeping default offset: {self.time_offset.total_seconds():.2f}s"
                )
                self.last_sync = time.time()

    def __call__(self, request):
        # Check if we need to resync
        if time.time() - self.last_sync > self.sync_interval:
            # Do sync in background thread to avoid blocking requests
            def background_sync():
                with self.lock:
                    self._sync_time_offset()

            threading.Thread(target=background_sync, daemon=True).start()

        response = self.get_response(request)
        return response
