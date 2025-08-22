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

        # Allow superusers
        try:
            if (
                hasattr(request, "user")
                and request.user.is_authenticated
                and request.user.is_superuser
            ):
                return self.get_response(request)
        except Exception:
            # In case auth backend is misconfigured, allow to avoid lockout
            return self.get_response(request)

        # Determine enabled state: prefer settings.SITE_ENABLED if present
        enabled = getattr(settings, "SITE_ENABLED", None)
        if enabled is None:
            try:
                # Import lazily to avoid AppRegistryNotReady during settings import
                from hunt.apps.main.models import SiteConfig

                enabled = SiteConfig.is_enabled()
            except Exception:
                enabled = True

        if not enabled:
            return render(request, "maintenance.html", status=503)

        return self.get_response(request)
