"""
Context processors for the main app.
"""

from django.conf import settings
from django.utils import timezone
from datetime import datetime
import zoneinfo


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
    """
    hunt_active = is_hunt_active()
    hunt_end_time_str = getattr(settings, "HUNT_END_TIME", None)

    return {
        "HUNT_YEAR": settings.HUNT_YEAR,
        "HUNT_ACTIVE": hunt_active,
        "HUNT_END_TIME": hunt_end_time_str,
    }
