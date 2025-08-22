from django.urls import path

from . import views

app_name = 'main'

urlpatterns = [
    path("", views.index, name="index"),
    path("overview/", views.overview, name="overview"),
    path("validate/", views.validate_flag, name="validate_flag"),
    path("support/", views.support, name="support"),
    path("toggledark/", views.dark_mode, name="toggledark"),
    path("challenge/<int:challenge_id>", views.challenge_detail, name="challenge_detail")
]