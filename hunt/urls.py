from django.contrib import admin
from django.urls import include, path
from hunt.apps.main.views import challenge_163624_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("social_django.urls", namespace="social")),
    path("", include("hunt.apps.auth.urls", namespace="auth")),
    path("main/", include("hunt.apps.main.urls", namespace="main")),
    path("logging/", include("hunt.apps.logging.urls", namespace="logging")),
    path("163624/", challenge_163624_view, name="challenge_163624"),
]

# Custom error handlers
handler404 = "hunt.apps.main.views.custom_404_view"
