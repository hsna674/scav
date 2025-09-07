import logging
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone

from .models import ActivityLog, ActivityType, PageView

logger = logging.getLogger(__name__)


class ActivityLoggingMiddleware(MiddlewareMixin):
    """Middleware to log page views and general activity"""

    # Paths to exclude from logging (static files, admin media, etc.)
    EXCLUDED_PATHS = [
        "/static/",
        "/admin/jsi18n/",
        "/favicon.ico",
        "/robots.txt",
    ]

    # Paths that should be logged as page views
    LOGGED_PATHS = [
        "/",
        "/challenge/",
        "/support/",
        # Removed deprecated /overview/ path
    ]

    def process_request(self, request):
        """Log page views for authenticated users"""

        # Skip if path should be excluded
        if any(request.path.startswith(excluded) for excluded in self.EXCLUDED_PATHS):
            return None

        # Only log for authenticated users (or specific paths for anonymous)
        if request.user.is_authenticated:
            # Log page view
            try:
                PageView.objects.create(
                    user=request.user,
                    path=request.path,
                    ip_address=self.get_client_ip(request),
                    user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                    referer=request.META.get("HTTP_REFERER", "")[:500],
                )

                # Log general activity for important pages
                if any(request.path.startswith(path) for path in self.LOGGED_PATHS):
                    ActivityLog.objects.create(
                        user=request.user,
                        activity_type=ActivityType.PAGE_VIEW,
                        ip_address=self.get_client_ip(request),
                        user_agent=request.META.get("HTTP_USER_AGENT", ""),
                        details={
                            "path": request.path,
                            "method": request.method,
                            "referer": request.META.get("HTTP_REFERER", ""),
                        },
                    )
            except Exception as e:
                # Don't let logging errors break the request
                logger.error(f"Error logging activity: {e}")

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
                "timestamp": timezone.now().isoformat(),
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
                    "timestamp": timezone.now().isoformat(),
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
