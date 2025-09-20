"""
Middleware to disable caching for debugging timezone issues
"""


class NoCacheMiddleware:
    """Middleware to disable all caching during debugging"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Add no-cache headers
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response["Pragma"] = "no-cache"
        response["Expires"] = "0"

        return response
