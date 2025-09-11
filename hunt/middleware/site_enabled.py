from django.shortcuts import render
from django.conf import settings


def _exempt_prefixes():
    return (
        "/admin/",
        "/static/",
        getattr(settings, "STATIC_URL", "/static/"),
        "/login/",
        "/logout/",
        "/complete/",  # social-auth completion callbacks
    )


def is_exempt_path(path):
    # Allow root only exactly, to enable redirect to /login/
    if path == "/":
        return True
    for prefix in _exempt_prefixes():
        if prefix and path.startswith(prefix):
            return True
    return False


class SiteEnabledMiddleware:
    """Middleware that blocks access when site is disabled except for superusers and exempt paths.

    Uses settings.SITE_ENABLED when defined; otherwise falls back to the DB-backed SiteConfig.
    Add to MIDDLEWARE after AuthenticationMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Allow exempt paths immediately
        if is_exempt_path(path):
            return self.get_response(request)

        # Allow superusers and committee members
        try:
            if (
                hasattr(request, "user")
                and request.user.is_authenticated
                and (request.user.is_superuser or request.user.is_committee)
            ):
                return self.get_response(request)
        except Exception:
            # In case auth backend is misconfigured, allow to avoid lockout
            return self.get_response(request)

        # Determine site availability using the control system
        try:
            # Import lazily to avoid circular imports
            from hunt.apps.main.context_processors import is_site_available

            site_available = is_site_available()
        except Exception:
            # Fallback to True if there's an error to avoid lockout
            site_available = True

        if not site_available:
            # Get site start time for the maintenance page
            site_start_time = getattr(settings, "SITE_START_TIME", None)
            context = {
                "SITE_START_TIME": site_start_time,
            }
            return render(request, "maintenance.html", context, status=503)

        return self.get_response(request)
