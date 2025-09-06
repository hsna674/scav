"""
Context processors for the main app.
"""

from django.conf import settings


def hunt_context(request):
    """
    Add hunt-related context variables to all templates.
    """
    return {
        "HUNT_YEAR": settings.HUNT_YEAR,
        "HUNT_ACTIVE": getattr(settings, "HUNT_ACTIVE", True),
    }
