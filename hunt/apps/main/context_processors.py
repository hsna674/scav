"""
Context processors for the main app.
"""

from django.conf import settings
from django.utils import timezone
from datetime import datetime
import zoneinfo
import logging
import os

from .discord_utils import send_hunt_end_notification

logger = logging.getLogger(__name__)


def is_hunt_active():
    """
    Determine if the hunt is currently active based on manual control and end time.
    """
    # Check manual control first
    manual_control = getattr(settings, "HUNT_MANUAL_CONTROL", True)
    if not manual_control:
        return False

    # Check if hunt has ended based on time
    hunt_end_time_str = getattr(settings, "HUNT_END_TIME", None)
    if hunt_end_time_str:
        try:
            # Parse the end time string
            est = zoneinfo.ZoneInfo("America/New_York")
            hunt_end_time = datetime.strptime(hunt_end_time_str, "%Y-%m-%d %H:%M:%S")
            hunt_end_time = hunt_end_time.replace(tzinfo=est)

            # Check if current time is past end time
            current_time = timezone.now()
            if current_time >= hunt_end_time:
                return False
        except (ValueError, TypeError):
            # If there's an error parsing the time, default to manual control
            pass

    return True


def hunt_context(request):
    """
    Add hunt-related context variables to all templates.
    Also checks if hunt has just ended and triggers Discord notification.
    """
    hunt_active = is_hunt_active()
    hunt_end_time_str = getattr(settings, "HUNT_END_TIME", None)

    # Check and notify if hunt has just ended (only on main pages to avoid spam)
    if request.path in ["/", "/main/", "/hunt/"] or request.path.startswith("/main/"):
        check_and_notify_hunt_end()

    return {
        "HUNT_YEAR": settings.HUNT_YEAR,
        "HUNT_ACTIVE": hunt_active,
        "HUNT_END_TIME": hunt_end_time_str,
    }


def check_and_notify_hunt_end():
    """
    Check if hunt has just ended and send Discord notification if needed.
    Uses a lock file to ensure notification is only sent once.
    """
    # Define lock file path
    lock_file_path = "/tmp/hunt_end_notification_sent.lock"

    # Check if notification has already been sent
    if os.path.exists(lock_file_path):
        return

    # Check if hunt is still active
    if is_hunt_active():
        return

    # Hunt has ended, send notification
    try:
        logger.info("Sending hunt end notification to Discord...")
        send_hunt_end_notification()

        # Create lock file to prevent duplicate notifications
        with open(lock_file_path, "w") as f:
            f.write(f"Hunt end notification sent at {timezone.now()}")

        logger.info("Successfully sent hunt end notification!")

    except Exception as e:
        logger.error(f"Failed to send hunt end notification: {e}")
