from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("social_django.urls", namespace="social")),
    path("", include("hunt.apps.auth.urls", namespace="auth")),
    path("main/", include("hunt.apps.main.urls", namespace="main")),
    path("logging/", include("hunt.apps.logging.urls", namespace="logging")),
]
