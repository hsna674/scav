import logging
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone

from .models import ActivityLog, ActivityType

logger = logging.getLogger(__name__)


class ActivityLoggingMiddleware(MiddlewareMixin):
    """Middleware for activity logging - page view logging removed for performance"""

    def process_request(self, request):
        """Process requests - page view logging has been removed for performance"""
        # Page view logging removed to improve performance
        # Previously logged every authenticated user request to database
        return None

    def get_client_ip(self, request):
        """Get the client's IP address"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip


@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    """Log when a user logs in"""
    try:
        ActivityLog.objects.create(
            user=user,
            activity_type=ActivityType.LOGIN,
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            details={
                "login_method": "oauth",  # Since you're using Ion OAuth
                "timestamp": timezone.localtime(timezone.now()).isoformat(),
            },
        )
    except Exception as e:
        logger.error(f"Error logging login: {e}")


@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    """Log when a user logs out"""
    try:
        if user:  # User might be None if session expired
            ActivityLog.objects.create(
                user=user,
                activity_type=ActivityType.LOGOUT,
                ip_address=get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                details={
                    "logout_method": "manual",
                    "timestamp": timezone.localtime(timezone.now()).isoformat(),
                },
            )
    except Exception as e:
        logger.error(f"Error logging logout: {e}")


def get_client_ip(request):
    """Helper function to get client IP"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip
